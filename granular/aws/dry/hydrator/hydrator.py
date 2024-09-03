import os
from argparse import ArgumentParser
import shutil
from datetime import datetime as dt
import logging
from enum import StrEnum, auto
import re
from pathlib import Path
import json


class Operation(StrEnum):
    INIT = auto()
    PLAN = auto()
    APPLY = auto()
    DESTROY = auto()
    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        return None

class BLOCK(StrEnum):
    INPUTS = auto()
    INCLUDE = auto()
    LOCALS = auto()
    REMOTE_STATE = auto()
    TERRAFORM = auto()
    def __repr__(self):
        return self.as_key()
    
    def as_key(self):
        return self.value.lower()

CONFIG_FILE = Path('terragrunt.hcl')
RUN_DIR = Path('_hydrator')
SUB_REPLACE = '%|||||'
QUOTE_REPLACE = '`````'
INC_PREFIX = 'include_'
TF_RUN_FORMAT = 'cd _hydrator && terraform {}'
LOG_LEVEL = logging.INFO

def log(msg: str, level=logging.DEBUG):
    if LOG_LEVEL <= level:
        print(f'[{dt.now().strftime("%Y-%m-d %H:%M:%S")}]: {msg}')

class Hydrator:
    def __init__(self, operation: str):
        self.operation = Operation(operation)
        self.config = None

    def run(self):
        if self.operation == Operation.DESTROY:
            self._tf_run(self.operation)
        else:
            self._parse_config()._copy()._set_vars()._init(self.operation == Operation.INIT)._tf_run(self.operation)

    def _init(self, no_op=False):
        tf = RUN_DIR / '.terraform'
        if not (no_op or tf.exists()):
            self._tf_run(Operation.INIT)
        return self

    def _tf_run(self, op: Operation):
        os.system(TF_RUN_FORMAT.format(op.name.lower()))

    def _set_vars(self):
        inputs = self.config.get_block(BLOCK.INPUTS)
        if inputs is not None and len(inputs) > 0:
           dest = RUN_DIR / 'hydrator.auto.tfvars.json' 
           dest.write_text(json.dumps(inputs))
        return self

    def _copy(self):
        if not RUN_DIR.exists():
            log(f"New run, creating '{RUN_DIR}' directory", logging.INFO)
            RUN_DIR.mkdir()

        self.files = []

        # `terraform` block must have a `source` attribute
        tf_source = Path(self.config.get_block(BLOCK.TERRAFORM)['source'])
        for f in tf_source.glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate']:
                    raise FileExistsError(f"'{tf_source}' directory contains a state file, cannot apply a Terraform template with existing state")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json']:
                    self.files.append(f)
        if len(self.files) == 0:
            raise RuntimeError(f'Teffaform files not found in {tf_source.absolute()}')

        for f in Path('./').glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate']:
                    raise FileExistsError(f"Cannot run a template with an existing state file (found in the current directory)")
                elif any([f.name == fe.name for fe in self.files]):
                    raise FileExistsError(f"File '{f.name}' exists in both local directory and target Terraform template directory")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json']:
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
                    rel_path = os.path.relpath(source_path, RUN_DIR)
                    txt = txt.replace(p[1], f'source = "{rel_path}"')
                    path_in_run.write_text(txt)

        # Set the remote state if needed
        remote_state = self.config.get_block(BLOCK.REMOTE_STATE)
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
    
    def _parse_config(self):
        # self._reset()   
        self.config = TerragruntConfig(CONFIG_FILE)
        log(f'Parsed config: {self.config}')
        return self

class TerragruntConfig:
    def __init__(self, config_file: Path, required_blocks=[BLOCK.TERRAFORM]):
        self.config_file = config_file
        self.required_blocks = required_blocks
        self.config = {}

        # TODO: refactor - remove this object level property
        self.locals = {}
        self.known_functions = {
            'get_env': self._get_env, 
            'file': self._file, 
            'find_in_parent_folders': self._find_in_parent_folders,
            'get_terragrunt_dir': self._get_terragrunt_dir,
            'jsondecode': self._jsondecode,
            'path_relative_to_include': self._path_relative_to_include
        }

        self._parse_config()

    def __repr__(self) -> str:
        return str(self.config)

    def get_block(self, block: BLOCK):
        return self.config.get(block.as_key(), None)

    def _parse_config(self):

        if not self.config_file.exists():
            raise FileNotFoundError(f'{self.config_file} is not found')

        config_str = self.config_file.read_text()
        flags = re.IGNORECASE | re.MULTILINE | re.DOTALL

        # One way to parse HCL is by converting it to JSON
        config = re.subn('\s*#[^\n]*', '', config_str)                          # remove comments
        config = re.subn('\${', SUB_REPLACE, config[0], flags)                  # temporarily mask interpolation (start of)
        config = re.subn('(^|\n)include\s+"([^\s"]+)"\s*{', INC_PREFIX + '\\2 {', config[0], flags)     # parse imports: `import "name" {` with `import_name {`
        config = re.subn('"', QUOTE_REPLACE, config[0], flags)                  # temporarily mask double quotes
        config = re.subn('([^\s\n=\$]+)\s*=', ',"\\1":', config[0], flags)      # replace `name =` with `,"name":`
        config = re.subn('([^\s\n:{]+)\s*{', ',"\\1": {', config[0], flags)     # replace `name {` with `,"name": {`
        config = re.subn(':\s*([^\s\d"{][^\n$]*)', ': "\\1"', config[0], flags) # wrap simple non-numeric values into double quotes
        config = re.subn('\s*\n\s*', '', config[0], flags)                      # remove empty space
        config = re.subn('{,', '{', config[0], flags)                           # remove extra commas after `{` (introduced by previous substitutions)
        config = re.subn('^,', '', config[0], flags)                            # remove extra commas at the start of line
        config = re.subn('"\^\^', '"', config[0], flags)                        # remove extra double quotes introduced earlier (from the string start)
        config = re.subn('\^\^"', '"', config[0], flags)                        # remove extra double quotes from string ends
        conf_str = config[0].replace(': "true"', ': true').replace(': "false"', ': false')  # unwrap booleans
        config = json.loads(f"{{{conf_str}}}")
        log(f'Config: {config}')

        # If `terraform` node is required it must have `source` attribute
        block = BLOCK.TERRAFORM
        block_key = block.as_key()
        tf = config.get(block_key, None)
        if block in self.required_blocks and (tf is None or tf.get('source', None) is None):
            raise LookupError(f'Reference to source terraform template is not found')
        if tf is not None:
            tf['source'] = tf.get('source').replace(QUOTE_REPLACE, '')
            self.config[block_key] = tf
        log(f'{block_key}: {tf}')

        # Following nodes are processed in the common way, must start with `locals`
        for block in [BLOCK.LOCALS, BLOCK.INPUTS, BLOCK.REMOTE_STATE]:
            block_key = block.as_key()
            _, res = self._resolve(config.get(block_key, None), block_type=block, is_recursive=False)

            # These are top level blocks, do not store null for them
            if res:
                self.config[block_key] = res if res is not None else {}
            log(f'{block_key}: {res}')

        # Resolve includes
        block = BLOCK.INCLUDE
        includes = {}
        for k in config:
            if k.startswith(INC_PREFIX):
                include = self._parse_include(config[k])

                # Extract remote state information separately
                remote_state_key = BLOCK.REMOTE_STATE.as_key()
                if remote_state_key in include:
                    self.config[remote_state_key] = include[remote_state_key]
                includes[k[len(INC_PREFIX):]] = include
        if len(includes):
            self.config[block.as_key()] = includes

        return self

    def _parse_include(self, config: dict) -> dict:
        """Parse the `include "name ` directive"""

        # `must have a `path` attribute
        path = config.get('path', None)
        if path is None:
            raise LookupError('include must have a `path`')
        
        # Resolve path, can be a function or local
        _, path = self._resolve(path, block_type=BLOCK.INCLUDE)
        include = TerragruntConfig(Path(path), required_blocks=[])

        return include.config

    def _resolve(self, value, block_type: BLOCK=BLOCK.LOCALS, is_recursive=False):
        """Return a value with all the locals and functions resolved"""

        # Nothing to resolve
        if value is None:
            return True, None

        local_must_exist=(block_type != BLOCK.LOCALS)

        if isinstance(value, dict):
            resolved = {}
            to_process = list(value.keys())
            while to_process:
                key = to_process.pop(0)
                is_ok, res = self._resolve(value[key], block_type=block_type, is_recursive=True)
                if is_ok:
                    resolved[key] = res
                    if block_type == BLOCK.LOCALS and not is_recursive:
                        # Store only top level locals
                        self.locals[key] = res
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
            # Actually, in Python it will be parsed `x: 'jsondecode(...)'` so we can test for it being a string becasue Terraform uses only " for strings
            value = value.replace(QUOTE_REPLACE, '"')
            value = value.replace(SUB_REPLACE, '${')
            log(f'Resolving: {value}')

            if value.startswith('local.'):
                # For now assume this is a single value, not an operation. It can be a nested property lookup
                v = self._get_local(value)
                if v is not None:
                    return True, v
                elif local_must_exist:
                    raise LookupError(f"'{value}' not found in locals")
                else:
                    return False, None
            
            if value.startswith('"') and value.endswith('"'):
                # This is a true string, strip the quotes
                is_ok, res = self._replace_locals(value.strip('"'), local_must_exist=local_must_exist)
                if is_ok:
                    res = self._replace_functions(res)
                return is_ok, res
            
            elif self._is_function(value):
                return self._exec_function(value)
            
            raise RuntimeError(f"Should never get here: {value}")
        
        else:
            # Boolean or number, no need to process
            return True, value

    def _get_local(self, key: str):
        if key.startswith('local.'):
            key = key[len('local.'):]
        lookup = self.locals
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
        log(param_str)
        if len(param_str) == 0:
            # Function without parameters
            return True, self.known_functions[func]()
        
        if param_str.count(',') == 0:
            # A single parameter
            is_ok, res = self._resolve(param_str)
            if is_ok:
                return True, self.known_functions[func](res)
            return False, None
        
        params = []
        i = 0

        if '${' in param_str:
            param_str = self._replace_functions(param_str)
        while i < len(param_str):
            if param_str[i] == '"':
                j = i + 1
                while j < len(param_str) and param_str[j] != '"':
                    j += 1
                if j < len(param_str):
                    params.append(param_str[i:j+1])
                else:
                    raise RuntimeError(f'Unclosed string in {param_str} from position {i}')
                j += 1
            elif self._is_function(param_str[i:]):
                f = self._extract_function(param_str[i:])
                params.append(f)
                j = i + len(f)
            else:
                raise RuntimeError(f"Should never get here: {param_str}")
            
            while j < len(param_str) and param_str[j] in [' ', ',']:
                j += 1
            i = j

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
        # return str(Path(".").absolute())

    def _file(self, path: str) -> str:
        p = Path(path.strip(' "'))
        return p.read_text()

    def _jsondecode(self, obj: str) -> dict:
        return json.loads(obj)

    def _find_in_parent_folders(self, name='terragrunt.hcl') -> Path:
        def find_recursive(parent: Path):
            f = parent / name
            if f.exists():
                return f 
            return find_recursive(parent / '../')
        
        return find_recursive(Path('../'))

    def _path_relative_to_include(self):
        caller = self._get_terragrunt_dir()
        return caller.relative_to(self.config_file.parent.absolute().resolve())


def get_args():
    parser = ArgumentParser(
        description='Run terragrunt template without using the Terragrunt'
    )
    parser.add_argument(
        'operation',
        default=Operation.PLAN.name.lower(),
        help=f'Terraform operation to run, one of {[op.name.lower() for op in list(Operation)]}'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    hydrator = Hydrator(args.operation)
    hydrator.run()