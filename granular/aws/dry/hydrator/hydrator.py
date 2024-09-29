import os
from argparse import ArgumentParser
import shutil
from datetime import datetime as dt
import logging
# from enum import StrEnum, auto
from enum import Enum
import re
from pathlib import Path
import json

# class Operation(StrEnum):
#     INIT = auto()
#     PLAN = auto()
#     APPLY = auto()
#     DESTROY = auto()
#     @classmethod
#     def _missing_(cls, value):
#         value = value.lower()
#         for member in cls:
#             if member.value == value:
#                 return member
#         return None

# class Block(StrEnum):
#     INPUTS = auto()
#     INCLUDE = auto()
#     LOCALS = auto()
#     REMOTE_STATE = auto()
#     TERRAFORM = auto()

class Operation(Enum):
    INIT = 0
    PLAN = 1
    APPLY = 2
    DESTROY = 3
    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.name.lower() == value:
                return member
        return None
    
class Block(Enum):
    INPUTS = 0
    INCLUDE = 1
    LOCALS = 2
    REMOTE_STATE = 3
    TERRAFORM = 4
    def val(self):
        return self.name.lower()

CONFIG_FILE_NAME = 'terragrunt.hcl'
RUN_DIR = Path('_hydrator')
SUB_REPLACE = '§|'
QUOTE_REPLACE = '`'
QUOTE_ESCAPE_REPLACE = "'"
INC_PREFIX = 'include_'
TF_RUN_FORMAT = 'cd _hydrator && terraform {}'
LOG_LEVEL = logging.INFO

def log(msg: str, level=logging.DEBUG):
    if LOG_LEVEL <= level:
        print(f'[{dt.now().strftime("%Y-%m-d %H:%M:%S")}]: {msg}')

class Hydrator:
    def __init__(self, operation: str, allow_state=False, prefix=''):
        self.operation = Operation(operation)
        self.allow_state = allow_state
        self.prefix = prefix
        self.config_parser = None

    def run(self):
        # If running only against a single state then it would be possible to avoid running all the steps when Destroying, but
        # that won't work if the same configuration is used to to deploy to different states (e.g. dev and test in the same target
        # environment but everything is the same, controlled by some prefix. Therefore all the operations will go throu the same steps
        res = self.parse_config()._copy()._set_vars()._init(self.operation == Operation.INIT)._tf_run(self.operation)
        if res > 0:
            # Signal failure to the caller, stopping here
            quit()

        if self.operation == Operation.APPLY:
            # Backup the lock file if not exists locally
            lock_file = Path('.terraform.lock.hcl')
            if not lock_file.exists() and (RUN_DIR / lock_file).exists():
                shutil.copy(RUN_DIR / lock_file, lock_file)

            # Backup the local state if existing state files are allowed
            state_file = RUN_DIR / 'terraform.tfstate'
            if self.allow_state and state_file.exists():
                shutil.copy(state_file, Path('./'), )

    def _init(self, no_op=False):
        tf = RUN_DIR / '.terraform'
        if not (no_op or tf.exists()):
            self._tf_run(Operation.INIT)
        return self

    def _tf_run(self, op: Operation):
        return os.system(TF_RUN_FORMAT.format(op.name.lower()))

    def _set_vars(self):
        inputs = self.config_parser.get_block(Block.INPUTS)
        if inputs is not None and len(inputs) > 0:
           dest = RUN_DIR / 'hydrator.auto.tfvars.json' 
           dest.write_text(json.dumps(inputs))
        return self

    def _copy(self):
        if not RUN_DIR.exists():
            log(f"New run, creating '{RUN_DIR}' directory", logging.INFO)
            RUN_DIR.mkdir()

        self.files = []

        # `terraform` block must have a `source` attribute. Copy files from there
        tf_source = Path(self.config_parser.get_block(Block.TERRAFORM)['source'])
        for f in tf_source.glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate']:
                    # State files in source modules are never allowed, they make no sense because they may/will be reused
                    raise FileExistsError(f"'{tf_source}' directory contains a state file, cannot apply a Terraform template with existing state")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json']:
                    self.files.append(f)
        if len(self.files) == 0:
            raise RuntimeError(f'Teffaform files not found in {tf_source.absolute()}')

        # Files local to config
        for f in Path('./').glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate'] and not self.allow_state:
                    raise FileExistsError(f"State files are not allowed in the current configuration, run with `--allow-state` to enable")
                elif any([f.name == fe.name for fe in self.files]):
                    raise FileExistsError(f"File '{f.name}' exists in both local directory and target Terraform template directory")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json'] or f.name.lower() in ['.terraform.lock.hcl', 'terraform.tfstate']:
                    self.files.append(f)
        [shutil.copy(f, RUN_DIR) for f in self.files]
        
        # Resolve module relative paths
        log(f'Resolving module paths')
        for f in self.files:
            path_in_run = RUN_DIR / f.name
            txt = path_in_run.read_text()
            res = re.findall('module\s+"[^"]+"\s*\{([^}]+|\{[^}]*\})[^}]*(source\s*=\s*"([^"]+)")', txt, re.IGNORECASE | re.MULTILINE)
            if res:
                log(f'In file: {f}')
                for p in res:
                    source_path = (f.parent / p[2]).resolve().absolute()

                    # This should always use posix style separatator, even in Windows
                    rel_path = os.path.relpath(source_path, RUN_DIR).replace(os.sep, '/')
                    txt = txt.replace(p[1], f'source = "{rel_path}"')
                    path_in_run.write_text(txt)

        # Set the remote state if needed
        remote_state = self.config_parser.get_block(Block.REMOTE_STATE)
        if remote_state:
            log('Setting remote state')
            backend = remote_state['backend']
            for f in self.files:
                path_in_run = RUN_DIR / f.name
                txt = path_in_run.read_text()
                res = re.search('(backend\s+"([^"]+)"\s+\{(([^}{]*|\{[^}]*\})[^}]*)\})', txt, re.IGNORECASE | re.MULTILINE)
                if res:
                    log(f'In file: {f}')
                    if res[2] != backend:
                        RuntimeError(f'Invalid backend, expected {res[1]}, got {backend}')
                    if len(res[3].strip()) > 0:
                        RuntimeError(f'Backend configuration must be empty, found {res[2]}')
                    
                    # TODO: improve to handle non-string data types if provided, not needed for S3 now
                    hcl = f'\n    '.join([f'{k} = "{v}"' for k, v in remote_state['config'].items()])
                    txt = txt.replace(res[1], f'backend "{backend}" {{\n    {hcl}\n  }}')
                    path_in_run.write_text(txt)

        return self
    
    def parse_config(self): 
        config_file = Path(self.prefix + CONFIG_FILE_NAME)  
        self.config_parser = TerragruntConfigParser(config_file)
        return self

class TerragruntConfigParser:
    def __init__(self, config_file_path: Path, config_str=None, required_blocks=[Block.TERRAFORM]):
        self.config_file_path = config_file_path
        if config_str is None:
            if not config_file_path.exists():
                raise FileNotFoundError(f'{config_file_path} is not found')

            config_str = config_file_path.read_text()
        self.config_str = config_str
        self.required_blocks = required_blocks
        self.config = {}
        self.config[self._block_key(Block.LOCALS)] = {}

        self.known_functions = {
            'get_env': self._get_env, 
            'file': self._file, 
            'find_in_parent_folders': self._find_in_parent_folders,
            'get_terragrunt_dir': self._get_terragrunt_dir,
            'jsondecode': self._jsondecode,
            'path_relative_to_include': self._path_relative_to_include,
            'merge': self._merge,
            'lookup': self._lookup,
            'replace': self._replace
        }

        self._parse_config()

    def __repr__(self) -> str:
        return str(self.config)

    def get_block(self, block: Block):
        return self.config.get(self._block_key(block), None)

    def _block_key(self, block: Block) -> str:
        return block.val()

    def _parse_config(self):

        config_str = self.config_str.strip()
        if len(config_str) == 0:
            return self
        
        

        # One way to parse HCL is by converting it to JSON. Could also be done using existing 3rd party libraries but this is 
        # designed to work in constrained environments where only Python is avaiable with no additional libraries

        ops = [
            ('\s*#[^\n]*', ''),                                 # Remove comments
            ('\\\\"', QUOTE_ESCAPE_REPLACE),                    # Temporarily mask escaped strings
            ('\${', SUB_REPLACE),                               # TODO: is it really necessary? Temporarily mask interpolation (start of)
            (
                '(^|\n)\s*include\s+"([^\s"]+)"\s*{', 
                '\\1' + INC_PREFIX + '\\2 {'
            ),                                                  # Parse imports: `import "name" {` with `import_name {`, do this before double quote masking!
            ('"', QUOTE_REPLACE),                               # Temporarily mask double quotes. This is necesary to handle cases when
            ('(\n|^)\s*([^\s\n=\$]+)\s*=', '\\1,"\\2":'),       # Replace `name =` with `,"name":`
            ('(\n|^)\s*([^\s\n:{,"]+)\s*{', '\\1,"\\2": {'),    # Replace `name {` with `,"name": {`, this should only apply to top level parameters

            (':\s*(`[^`]*`)\s*((}|,))', ': "\\1"\\2'),          # Wrap the object string value into double quotes 
                      
            (':\s*([^\s\d[{"\'][^\n$]*)', ': "\\1"'),           # Wrap simple non-numeric values into double quotes
            ('\s*\n\s*', ' '),                                  # Compress empty space into a single space
            ('{(\s|\n)*,', '{'),                                # Remove extra commas after `{` which could've been introduced by the previous substitutions
            ('{\s*`', '{"`'), ('`\s*:', '`":'),                 # Wrap the object keys into double quotes
            (':\s*\[`', ': ["`'), 
            ('(:\s\["`[^]]*`)]', '\\1"]'),                      # Handle list edges
            (QUOTE_ESCAPE_REPLACE, '\\\\"'),                    # Restore masked escaped double quotes
        ]

        flags = re.IGNORECASE | re.MULTILINE | re.DOTALL      
        for p, r in ops:
            config_str = re.subn(p, r, config_str, flags=flags)[0]
        
        # Handle multi-element list inner parts
        while True:
            config = re.subn(':\s*\[([^]]*)`\s*,\s*`([^]]+)]', ': [\\1`", "`\\2]', config_str, flags=flags)
            if config[1] == 0:
                break
            config_str = config[0]

        # Remove extra commas at the boundaries                            
        config_str = config_str.strip(',')

        # Unwrap booleans and nulls which may've got wrapped into double quotes earlier
        conf_str = config_str.replace(': "true"', ': true').replace(': "false"', ': false').replace(': "null"', ': null')   

        log(f'Config str: {conf_str}')
        config = json.loads(f"{{{conf_str}}}")
        log(f'Config: {config}')

        # If `terraform` node is required it must have `source` attribute
        block = Block.TERRAFORM
        block_key = self._block_key(block)
        tf = config.get(block_key, None)
        if block in self.required_blocks and (tf is None or tf.get('source', None) is None):
            raise LookupError(f'Reference to source terraform template is not found')
        if tf is not None:
            tf['source'] = tf.get('source').replace(QUOTE_REPLACE, '')
            self.config[block_key] = tf
        log(f'{block_key}: {tf}')

        # Resolve includes first (which in Terragrunt seem to allow only fixed values or functions, no locals)
        block = Block.INCLUDE
        block_key = self._block_key(block)
        includes = {}
        for k in config:
            if k.startswith(INC_PREFIX):
                include = self._parse_include(config[k])

                # Extract remote state information separately
                remote_state_block_key = self._block_key(Block.REMOTE_STATE)
                if remote_state_block_key in include:
                    self.config[remote_state_block_key] = include[remote_state_block_key]
                includes[k[len(INC_PREFIX):]] = include
        self.config[block_key] = includes

        # Following nodes are processed in the common way, start with `locals`
        for block in [Block.LOCALS, Block.INPUTS, Block.REMOTE_STATE]:
            block_key = self._block_key(block)
            _, res = self._resolve(config.get(block_key, None), block_type=block, is_recursive=False)

            # These are top level blocks, do not store null for them
            if res is not None:
                self.config[block_key] = res  # if res is not None else {}
            log(f'{block_key}: {res}')

        log(f'Parsed config: {self.config}')
        return self

    def _parse_include(self, config: dict) -> dict:
        """Parse the `include "name ` directive"""

        # `must have a `path` attribute
        path = config.get('path', None)
        if path is None:
            raise LookupError('include must have a `path`')
        
        # Resolve path. Terragrunt allows functions for this but not `locals` 
        _, path = self._resolve(path, block_type=Block.INCLUDE)

        include = TerragruntConfigParser(Path(path), required_blocks=[])

        return include.config

    def _resolve(self, value, block_type: Block=Block.LOCALS, is_recursive=False):
        """Return a value with all the locals and functions resolved"""

        # Nothing to resolve
        if value is None:
            return True, None

        local_must_exist=(block_type != Block.LOCALS)

        if isinstance(value, dict):
            resolved = {}
            to_process = list(value.keys())
            while to_process:
                key = to_process.pop(0)
                is_ok, res = self._resolve(value[key], block_type=block_type, is_recursive=True)
                if is_ok:
                    # Key may be wrapped into QUOTE_REPLACE
                    k = key.strip(QUOTE_REPLACE)
                    resolved[k] = res
                    if block_type == Block.LOCALS and not is_recursive:
                        # Store only top level locals
                        self.config[self._block_key(Block.LOCALS)][k] = res
                elif not is_recursive:
                    # Dependency not found, this could only happen to locals, not inputs, put it back to queue but only if it wasn't the last one
                    if len(to_process) > 0:
                        to_process.append(key)
                    else:
                        raise LookupError(f"'Dependency for {value[key]}' not found")
                else:
                    # Must be also part of locals but is deeper in the hierarchy, stop here, this should abandon the full tree traversal
                    return False, None
        
            return True, resolved
        
        if isinstance(value, list):
            resolved = []
            for v in value:
                is_ok, res = self._resolve(v, block_type=block_type, is_recursive=True)
                if is_ok:
                    resolved.append(res)
                else:
                    return False, None
        
            return True, resolved

        elif isinstance(value, str):
            # Just because the value is string here doesn't mean it will be of string type becuase of the way we converted the HCL to JSON,
            # e.g. in `x = jsondecode(...)` is converted to `"x": "jsondecode(...)"` so value will appear as str type here but it is an object
   
            # Value may be wrapped in QUOTE_REPLACE, strip those. It may also contain QUOTE_REPLACE in it so convert it to double quote
            value = value.strip(QUOTE_REPLACE).replace(QUOTE_REPLACE, '"')
            value = value.replace(SUB_REPLACE, '${')
            log(f'Resolving: {value}')

            if value.startswith('local.'):
                # For now assume this is a single value, not an operation. It can be a nested property lookup
                log(f'Resolving local: {value}')
                v = self._get_local(value)
                if v is not None:
                    return True, v
                elif local_must_exist:
                    raise LookupError(f"'{value}' not found in locals")
                else:
                    return False, None
            
            elif value.startswith('include.'):
                log(f'Resolving include: {value}')
                v = self._get_include(value)
                return v is not None, v
            
            elif value.startswith('null'):
                log(f'Resolving null')
                return True, None
            
            elif value.startswith('{}'):
                log(f'Resolving empty object')
                return True, {}
            
            elif value.startswith('[]'):
                log(f'Resolving empty list')
                return True, []
            
            elif self._is_function(value):
                return self._exec_function(value)
            
            else:
                 # This is likely just a string, strip possible surrounding double quotes
                log(f'Resolving string: {value}')
                is_ok, res = self._replace_locals(value.strip('"'), local_must_exist=local_must_exist)
                if is_ok:
                    res = self._replace_functions(res)
                log(f'- resolved: {res}')
                return is_ok, res
            
            raise RuntimeError(f"Should never get here: {value}")
        
        else:
            # Boolean or number, no need to process
            return True, value

    def _get_local(self, key: str):
        if key.startswith('local.'):
            key = key[len('local.'):]
        lookup = self.config[self._block_key(Block.LOCALS)]
        keys = key.split('.')
        for key in keys:
            if '[' in key:
                i = key.index('[')
                if i > 0:
                    k = key[:i]
                    lookup = lookup.get(k, None)
                    if lookup is None:
                        return None

                k = key[i:]
                while k is not None and k.startswith('['):
                    i = k.index(']')
                    idx = int(k[1:i])
                    lookup = lookup[idx]
                    i += 1
                    k = None if i >= len(k) else k[i:]
            else:
                lookup = lookup.get(key, None)
                if lookup is None:
                    return None

        return lookup

    def _get_include(self, key: str):
        if key.startswith('include.'):
            key = key[len('include.'):]
        lookup = self.config[self._block_key(Block.INCLUDE)]
        for k in key.split('.'):
            res = lookup.get(k, None)
            if res is None:
                break
            else:
                lookup = res
        return res  

    def _is_function(self, value: str) -> bool:
        if not value.startswith('"'):
            for func in self.known_functions:
                if re.search(f'^{func}\s*\(', value):
                    return True
        return False

    def _replace_locals(self, value_str: str, local_must_exist=False) -> tuple[bool, str]:
        """ Interpolate the string by replacing all the occurrences of references to locals only"""

        # This is a string interpolation so must include `${...}`
        pattern = "(\$\{local.([^\s}]+)\})"
        while True:
            res = re.search(pattern, value_str, re.IGNORECASE)
            if res:
                full_local = res.group(1)
                key = res.group(2)
                v = self._get_local(key)
                if v is not None:
                    value_str = value_str.replace(full_local, str(v), 1)
                    continue
                elif local_must_exist:
                    raise LookupError(f"'{key}' not found in locals")
                return False, None
            break

        return True, value_str

    def _replace_functions(self, value_str: str):
        """ Interpolate the string by replacing all the occurrences of references to functions"""

        # Fancy regexes like `((\$\{)?\d[^"()\{\}/]*\([^()]*(\)*\s*)*)` would be really hard to construct here, e.g. for nested functions, safer to parse by walking along
        while True:
            if '${' in value_str:
                i = value_str.index('${')
            else:
                break

            j = i + 2
            func_str = value_str[j:]
            is_func = self._is_function(func_str)
            if not is_func:
                raise LookupError(f'Unknown function in "{func_str}" at the position {i}')
            
            in_string = False
            while (value_str[j] != '}' or in_string) and j < len(value_str):
                if value_str[j] == '"':
                    in_string = not in_string
                elif in_string and value_str[j] == '{' and value_str[j-1] == '$':
                    ## Nested function, need to solve it first
                    i = j - 1
                    in_string = False
                j += 1

            if j < len(value_str):
                is_ok, res = self._exec_function(value_str[i+2:j].strip())
                if is_ok:
                    value_str = f'{value_str[0:i]}{res}{value_str[j+1:]}'

        return value_str

    def _extract_function(self, value: str) -> str:
        """ Extract the full definition of the function at the start of the given value"""

        log(f'Extracting function from: {value}')

        # Fancy regexes like `'([^{(\s]+)\s*\(([^)]*)(\)*\s*)*'` won't be sufficient here, e.g. for nested functions, safer to parse by walking along
        lookup = re.search(f'(^([^\s\(]+)\s*\()', value)
        if not lookup:
            raise ValueError(f'Invalid function {value}')
        func = lookup.group(2)
        if func not in self.known_functions:
            raise ValueError(f'Uknown function {func}')
        
        i = len(lookup.group(1)) - 1
        count = 0
        in_string = False
        while i < len(value) - 1:
            i += 1
            if value[i] == '"':
                in_string = not in_string
                i += 1
                continue
            if in_string:
                continue

            if value[i] == '(':
                count += 1
                continue

            if value[i] == ')':
                if count == 0:
                    return value[0:i+1]
                else:
                    count -= 1

        return value
    
    def _exec_function(self, func_str: str):
        """Execute a given function"""

        lookup = re.search(f'(^([^\s\(]+)\s*\()', func_str)
        if not lookup:
            raise ValueError(f'Invalid function {func_str}')
        func = lookup.group(2)
        if func not in self.known_functions:
            raise ValueError(f'Uknown function {func}')

        log(f'Executing: {func_str}')
        
        param_str = func_str.strip()[len(lookup.group(1)):-1]
        if len(param_str) == 0:
            # Function without parameters
            return True, self.known_functions[func]()
        
        if param_str.count(',') == 0:
            # A single parameter
            is_ok, res = self._resolve(param_str)
            if is_ok:
                return True, self.known_functions[func](res)
            return False, None
        
        if '${' in param_str:
            param_str = self._replace_functions(param_str)

        params = []
        i = 0
        while i < len(param_str):
            if param_str[i] == ' ':
                i += 1
                continue

            if param_str[i] == '"':
                j = i + 1
                while j < len(param_str) and param_str[j] != '"':
                    j += 1
                if j < len(param_str):
                    # No trims here
                    params.append(param_str[i:j+1])
                else:
                    raise RuntimeError(f'Unclosed string in {param_str} from position {i}')
                i = j + 1
                if i < len(param_str) and param_str[i] == ',':
                    i += 1
            elif self._is_function(param_str[i:]):
                f = self._extract_function(param_str[i:])
                params.append(f)
                i = i + len(f)
                if i < len(param_str) and param_str[i] == ',':
                    i += 1
            elif param_str[i:].startswith('local.') or param_str[i:].startswith('include.'):
                j = i + len('local.')
                while j < len(param_str) and param_str[j] != ',':
                    j += 1
                params.append(param_str[i:j].strip())
                i = j + 1
            elif param_str[i:].startswith('null'):
                j = i + len('null')
                params.append('null')
                while j < len(param_str) and param_str[j] != ',':
                    j += 1
                i = j + 1
            elif param_str[i:].startswith('{}'):
                j = i + len('{}')
                params.append('{}')
                while j < len(param_str) and param_str[j] != ',':
                    j += 1
                i = j + 1
            elif param_str[i:].startswith('[]'):
                j = i + len('[]')
                params.append('[]')
                while j < len(param_str) and param_str[j] != ',':
                    j += 1
                i = j + 1
            else:
                raise RuntimeError(f"Should never get here: {param_str}")

        resolved_params = []
        for p in params:
            is_ok, p_res = self._resolve(p)
            if is_ok:
                resolved_params.append(p_res)
            else:
                return False, None
            
        return True, self.known_functions[func](*resolved_params)


    def _get_env(self, name: str, default=None) -> str:
        val = os.environ.get(name, default)
        return val

    def _get_terragrunt_dir(self) -> Path:
        return Path(".").absolute().resolve()

    def _file(self, path: str) -> str:
        p = Path(path.strip(' "'))
        return p.read_text()

    def _jsondecode(self, obj: str) -> dict:
        # Strip possible surrounding double quotes
        return json.loads(obj.strip('"'))

    def _find_in_parent_folders(self, name='terragrunt.hcl') -> Path:
        def find_recursive(parent: Path):
            f = parent / name
            if f.exists():
                return f
            if os.path.dirname(str(parent)) == str(parent):
                # We are at the root, stop
                raise FileNotFoundError(f'{name} not found')
            return find_recursive((parent / '../').resolve())
        
        return find_recursive(Path('../').resolve())

    def _path_relative_to_include(self) -> str:
        caller = self._get_terragrunt_dir()
        res = caller.relative_to(self.config_file_path.parent.absolute().resolve())

        # Need to use posix style separator here
        return str(res).replace(os.sep, '/')

    def _merge(self, dest: dict, src: dict) -> dict:
        # Do not update the destination dict directly, may end up re-writing state
        res = dest.copy()
        res.update(src)
        return res
    
    def _lookup(self, src: dict, attr, default):
        return src.get(attr, default)
    
    def _replace(self, value: str, old: str, new: str):
        return value.replace(old, new)

def get_args():
    parser = ArgumentParser(
        description='Run terragrunt template without using the Terragrunt'
    )
    parser.add_argument(
        'operation',
        default=Operation.PLAN.value,
        help=f'Terraform operation to run, one of {[op.name.lower() for op in list(Operation)]}'
    )
    parser.add_argument(
        '-s',
        '--allow-state',
        action='store_true',
        default=False,
        help='If specified then the `.tfstate` file will be allowed in the config directory'
    )
    parser.add_argument(
        '-p',
        '--prefix',
        default='',
        help='Prefix of the configuration file to use'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    hydrator = Hydrator(args.operation, args.allow_state, args.prefix)
    hydrator.run()