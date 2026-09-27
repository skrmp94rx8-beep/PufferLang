class PufferLang:
    class PLSyntaxError(Exception):
        pass
    class PLNameError(Exception):
        pass
    class PLUnknownTokenError(Exception):
        pass
    class PLDLLError(Exception):
        pass
    def __init__(self, source='', mode='pf'):
        self.source = source
        self.mode = mode
        self.tokens = []
        self.ast = []
        self.py_code = ''
        self._depth = 0      

    def lex(self):
        code = self.source
        tokens = []
        i = 0
        n = len(code)
        while i < n:
            c = code[i]
            if c == ' ' or c == '\t':
                i += 1
            elif c == '\n':
                tokens.append(('NL', '\n'))
                i += 1
            elif c == '"':
                i += 1
                s = ''
                while i < n and code[i] != '"':
                    s += code[i]
                    i += 1
                if i >= n:
                    raise Exception("incomplete quotes")
                i += 1
                tokens.append(('STR', s))
            elif c.isdigit() or (c == '.' and i + 1 < n and code[i + 1].isdigit()):
                num = ''
                while i < n and (code[i].isdigit() or code[i] == '.'):
                    num += code[i]
                    i += 1
                if '.' in num:
                    tokens.append(('FLOAT', float(num)))
                else:
                    tokens.append(('NUM', int(num)))
            elif code.startswith('NTCP(', i):
                i += 5                     
                start = i
                depth = 1
                while i < n and depth > 0:
                    if code[i] == '(':
                        depth += 1
                    elif code[i] == ')':
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                if depth != 0:
                    raise Exception("unclosed NTCP")
                raw = code[start:i]
                i += 1                     
                raw = raw.strip()
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1]
                elif raw.startswith("'") and raw.endswith("'"):
                    raw = raw[1:-1]
                tokens.append(('NTCP', raw))
            elif code.startswith('+C', i):
                tokens.append(('COND', '+C'))
                i += 2
            elif code.startswith('+R', i):
                tokens.append(('RECUR', '+R'))
                i += 2
            elif code.startswith('+>', i):
                tokens.append(('THEN', '+>'))
                i += 2
            elif code.startswith('!>', i):
                tokens.append(('ELSE', '!>'))
                i += 2
            elif code.startswith('==', i):
                tokens.append(('EQ', '=='))
                i += 2
            elif code.startswith('!=', i):
                tokens.append(('NE', '!='))
                i += 2
            elif code.startswith('<=', i):
                tokens.append(('LE', '<='))
                i += 2
            elif code.startswith('>=', i):
                tokens.append(('GE', '>='))
                i += 2
            elif c.isalpha() or c == '_':
                word = ''
                while i < n and (code[i].isalnum() or code[i] == '_'):
                    word += code[i]
                    i += 1
                if word in ('asg', 'int', 'str', 'float', 'bool'):
                    tokens.append(('KW', word))
                elif word == 'true':
                    tokens.append(('BOOL', True))
                elif word == 'false':
                    tokens.append(('BOOL', False))
                else:
                    tokens.append(('ID', word))
            elif code.startswith('=>', i):
                tokens.append(('ARROW', '=>'))
                i += 2
            elif code.startswith('<<', i):        
                tokens.append(('RET', '<<'))
                i += 2
            elif c == '<':
                tokens.append(('LT', '<'))
                i += 1
            elif c == '>':
                tokens.append(('GT', '>'))
                i += 1
            elif c == '?':
                tokens.append(('Q', '?'))
                i += 1
            elif c == ':':
                tokens.append(('COLON', ':'))
                i += 1
            elif c == '.':
                tokens.append(('DOT', '.'))
                i += 1
            elif c == '(':
                tokens.append(('LP', '('))
                i += 1
            elif c == ')':
                tokens.append(('RP', ')'))
                i += 1
            elif code.startswith('+&', i):
                tokens.append(('FUNC', '+&'))
                i += 2
            elif code.startswith('+M', i):
                tokens.append(('IMP', '+M'))
                i += 2
            elif code.startswith('+OOBV', i):
                tokens.append(('OOBV', '+OOBV'))
                i += 5
            elif code.startswith('+O', i):
                tokens.append(('OWNER', '+O'))
                i += 2
            elif code.startswith('/O', i):
                tokens.append(('SLASH_O', '/O'))
                i += 2
            elif code.startswith('<<', i):
                tokens.append(('RET', '<<'))
                i += 2
            elif c in '+-*/%':
                tokens.append(('OP', c))
                i += 1
            elif c == '[':
                tokens.append(('LB', '['))
                i += 1
            elif c == ']':
                tokens.append(('RB', ']'))
                i += 1
            elif c == ',':
                tokens.append(('COMMA', ','))
                i += 1
            else:
                raise self.PLNameError(f"what the hell is {c!r} in {i}")
        tokens.append(('EOF', None))
        self.tokens = tokens
        return tokens

    def parse(self):
        self.pos = 0
        stmts = []
        self._skip_newlines()
        while self._peek()[0] != 'EOF':
            stmts.append(self._parse_stmt())
            if self._peek()[0] == 'NL':
                self._skip_newlines()
            elif self._peek()[0] != 'EOF':
                raise self.PLSyntaxError(f"\\n needed:{self._peek()}")
        self.ast = stmts
        return stmts

    def _peek(self, off=0):
        return self.tokens[self.pos + off]

    def _next(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, kind, value=None):
        t = self._next()
        if t[0] != kind or (value is not None and t[1] != value):
            raise self.PLSyntaxError(f"expected {kind} {value}, but input is {t}")
        return t

    def _skip_newlines(self):
        while self._peek()[0] == 'NL':
            self._next()

    def _parse_import(self):
        self._next()
        name = self._expect('ID')[1]
        path = None
        if self._peek()[0] == 'DOT':
            self._next()
            ext = self._expect('ID')[1]
            path = f"{name}.{ext}"
        if self._peek()[0] == 'STR':
            path = self._next()[1]
        return {'type': 'import', 'name': name, 'path': path}

    def _parse_recurring(self):
        self._next()  
        self._expect('LP')
        condition = self._parse_expr()
        self._expect('RP')
        self._expect('THEN')  
        self._expect('LB')
        
        body = []
        self._depth += 1
        self._skip_newlines()
        while self._peek()[0] != 'RB':
            body.append(self._parse_stmt())
            if self._peek()[0] == 'NL':
                self._skip_newlines()
        self._expect('RB')
        self._depth -= 1
        
        return {
            'type': 'recurring',
            'condition': condition,
            'body': body,
        }

    def _parse_stmt(self):
        t = self._peek()
    
        if t == ('KW', 'asg'):
            return self._parse_define()
        if t == ('FUNC', '+&'):
            return self._parse_funcdef()
        if t == ('OWNER', '+O'):
            return self._parse_owner()
        if t == ('OOBV', '+OOBV'):
            return self._parse_oobv()
        if t == ('COND', '+C'):    
            return self._parse_condition()
        if t == ('RECUR', '+R'):
            return self._parse_recurring()
        if t[0] == 'NTCP':
            self._next()
            return {'type': 'ntcp', 'code': t[1]}
        if t == ('COLON', ':'):
            if self.mode == 'pdl' and self._depth == 0:
                raise self.PLDLLError("pdl files can only +& and asg at top level bruh")
            return self._parse_syscall()
        if t == ('IMP', '+M'):
            if self.mode == 'pdl' and self._depth == 0:
                raise self.PLDLLError("no chain import plz")
            return self._parse_import()
        if t[0] == 'ID' or t[0] == 'Q' or t[0] == 'SLASH_O':
            if self.mode == 'pdl' and self._depth == 0:
                raise self.PLDLLError("pdl files cannot express on the top level")
            return {'type': 'exprstmt', 'value': self._parse_expr()}
        raise self.PLUnknownTokenError(f"what the hell is {t}")
    
    def _parse_define(self):
        self._next()
        name = self._expect('ID')[1]
        self._expect('LT')
        vartype = self._expect('KW')[1]
        if vartype not in ('int', 'str', 'float', 'bool'):
            raise self.PLNameError(f"unsupported type: {vartype}")
        self._expect('GT')
        self._expect('ARROW')
        value = self._parse_value()
        return {'type': 'define', 'name': name, 'vartype': vartype, 'value': value}

    def _parse_expr(self):
        return self._parse_compare()
    
    def _parse_compare(self):
        left = self._parse_add()
        while self._peek()[0] in ('EQ', 'NE', 'LE', 'GE', 'LT', 'GT'):
            op = self._next()[1]
            right = self._parse_add()
            left = {'kind': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def _parse_owner(self):
        self._next()  
        name = self._expect('ID')[1]
        return {'type': 'ownerdef', 'name': name}

    def _parse_oobv(self):
        self._next()  
        owner = self._expect('ID')[1]
        self._expect('COMMA')
        field = self._expect('ID')[1]
        self._expect('COMMA')
        vartype = self._expect('KW')[1]
        if vartype not in ('int', 'str', 'float'):
            raise self.PLNameError(f"unsupported type: {vartype}")
        self._expect('COMMA')
        value = self._parse_value()
        return {
            'type': 'oobvdef',
            'owner': owner,
            'field': field,
            'vartype': vartype,
            'value': value,
        }

    def _parse_add(self):
        left = self._parse_mul()
        while self._peek()[0] == 'OP' and self._peek()[1] in '+-':
            op = self._next()[1]
            right = self._parse_mul()
            left = {'kind': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def _parse_mul(self):
        left = self._parse_atom()
        while self._peek()[0] == 'OP' and self._peek()[1] in '*/%':
            op = self._next()[1]
            right = self._parse_atom()
            left = {'kind': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def _parse_atom(self):
        t = self._peek()
        if t[0] == 'FLOAT' or t[0] == 'NUM':
            self._next()
            return {'kind': 'lit', 'value': t[1]}
        if t[0] == 'NTCP':
            self._next()
            return {'kind': 'ntcp', 'code': t[1]}
        if t[0] == 'STR':
            self._next()
            return {'kind': 'lit', 'value': t[1]}
        if t[0] == 'BOOL':
            self._next()
            return {'kind': 'lit', 'value': t[1]}
        if t[0] == 'Q':
            self._next()
            name = self._expect('ID')[1]
            if self._peek()[0] == 'LP':
                self._next()
                args = []
                if self._peek()[0] != 'RP':
                    args.append(self._parse_expr())
                    while self._peek()[0] == 'COMMA':
                        self._next()
                        args.append(self._parse_expr())
                self._expect('RP')
                return {'kind': 'call', 'name': name, 'args': args}
            return {'kind': 'var', 'value': name}
        if t[0] == 'ID':
            self._next()
            if self._peek()[0] == 'LP':
                self._next()
                args = []
                if self._peek()[0] != 'RP':
                    args.append(self._parse_expr())
                    while self._peek()[0] == 'COMMA':
                        self._next()
                        args.append(self._parse_expr())
                self._expect('RP')
                return {'kind': 'call', 'name': t[1], 'args': args}
            raise self.PLSyntaxError(f"no brackets so you can only call function: {t[1]}")
        if t[0] == 'LP':
            self._next()
            e = self._parse_expr()
            self._expect('RP')
            return e
        if t[0] == 'SLASH_O':
            self._next()
            owner = self._expect('ID')[1]
            self._expect('DOT')
            field = self._expect('ID')[1]
            return {'kind': 'oobv_access', 'owner': owner, 'field': field}
        raise self.PLSyntaxError(f"value expected: {t}")

    def _parse_value(self):
        return self._parse_expr()

    def _parse_funcdef(self):
        self._next()
        name = self._expect('ID')[1]
        self._expect('LP')
        params = []
        if self._peek()[0] != 'RP':
            params.append(self._expect('ID')[1])
            while self._peek()[0] == 'COMMA':
                self._next()
                params.append(self._expect('ID')[1])
        self._expect('RP')
        self._expect('LB')
    
        body = []
        self._depth += 1              
        self._skip_newlines()
        while self._peek()[0] != 'RB':
            body.append(self._parse_stmt())
            if self._peek()[0] == 'NL':
                self._skip_newlines()
        self._expect('RB')
        self._depth -= 1           
    
        return {'type': 'funcdef', 'name': name, 'params': params, 'body': body}
        
    def _parse_syscall(self):
        self._expect('COLON')
        self._expect('ID', 'sys')
        self._expect('DOT')
        method = self._expect('ID')[1]

        if method == 'return':
            self._expect('RET')     
            self._expect('LP')      
            val = self._parse_expr()
            self._expect('RP')      
            return {'type': 'return', 'value': val}

        self._expect('LP')          
        if method == 'out':
            arg = self._parse_expr()
            self._expect('RP')
            return {'type': 'print', 'target': arg}
        if method == 'in':
            if self._peek()[0] == 'Q':
                self._next()
            name = self._expect('ID')[1]
            self._expect('RP')
            return {'type': 'input', 'name': name}

        raise self.PLNameError(f"no method called {method} in sys")

    def codegen(self):
        lines = []
        for stmt in self.ast:
            lines.append(self._gen_stmt(stmt))
        self.py_code = '\n'.join(lines)
        return self.py_code

    def _parse_condition(self):
        self._next()  
        self._expect('LP')
        condition = self._parse_expr()
        self._expect('RP')
    
        self._expect('THEN')
        self._expect('LB')
        then_body = []
        self._depth += 1
        self._skip_newlines()
        while self._peek()[0] != 'RB':
            then_body.append(self._parse_stmt())
            if self._peek()[0] == 'NL':
                self._skip_newlines()
        self._expect('RB')
        self._depth -= 1
    
        else_body = None
        if self._peek()[0] == 'ELSE':
            self._next()  
            self._expect('LB')
            else_body = []
            self._depth += 1
            self._skip_newlines()
            while self._peek()[0] != 'RB':
                else_body.append(self._parse_stmt())
                if self._peek()[0] == 'NL':
                    self._skip_newlines()
            self._expect('RB')
            self._depth -= 1
    
        return {
            'type': 'condition',
            'condition': condition,
            'then': then_body,
            'else': else_body,
        }

    def _gen_condition(self, stmt):
        cond = self._expr(stmt['condition'])
        lines = [f"if {cond}:"]
    
        then_code = []
        for s in stmt['then']:
            then_code.append(self._gen_stmt(s))
        if not then_code:
            then_code = ['pass']
        for line in then_code:
            for sub in line.split('\n'):
                lines.append('    ' + sub)
    
        if stmt['else']:
            lines.append('else:')
            else_code = []
            for s in stmt['else']:
                else_code.append(self._gen_stmt(s))
            if not else_code:
                else_code = ['pass']
            for line in else_code:
                for sub in line.split('\n'):
                    lines.append('    ' + sub)
    
        return '\n'.join(lines)

    def _gen_recurring(self, stmt):
        cond = self._expr(stmt['condition'])
        lines = [f"while {cond}:"]
        
        body_code = []
        for s in stmt['body']:
            body_code.append(self._gen_stmt(s))
        if not body_code:
            body_code = ['pass']
        for line in body_code:
            for sub in line.split('\n'):
                lines.append('    ' + sub)
        
        return '\n'.join(lines)

    def _gen_stmt(self, stmt):
        if stmt['type'] == 'define':
            v = self._expr(stmt['value'])
            return f"{stmt['name']}: {stmt['vartype']} = {v}"
        if stmt['type'] == 'ntcp':
            return stmt['code']
        if stmt['type'] == 'print':
            return f"print({self._expr(stmt['target'])})"
        if stmt['type'] == 'input':
            return f"{stmt['name']} = input()"
        if stmt['type'] == 'return':
            return f"return {self._expr(stmt['value'])}"
        if stmt['type'] == 'funcdef':
            return self._gen_funcdef(stmt)
        if stmt['type'] == 'exprstmt':
            return self._expr(stmt['value'])
        if stmt['type'] == 'import':
            return self._gen_import(stmt)
        if stmt['type'] == 'ownerdef':
            return self._gen_owner(stmt)
        if stmt['type'] == 'oobvdef':
            return self._gen_oobv(stmt)
        if stmt['type'] == 'condition':
            return self._gen_condition(stmt)
        if stmt['type'] == 'recurring':
            return self._gen_recurring(stmt)
        raise self.PLNameError(f"what the hell is {stmt}")

    def _expr(self, node):
        if node['kind'] == 'lit':
            return repr(node['value'])
        if node['kind'] == 'ntcp':
            return node['code']
        if node['kind'] == 'var':
            return node['value']
        if node['kind'] == 'binop':
            l = self._expr(node['left'])
            r = self._expr(node['right'])
            return f"({l} {node['op']} {r})"
        if node['kind'] == 'call':
            args = ', '.join(self._expr(a) for a in node['args'])
            return f"{node['name']}({args})"
        if node['kind'] == 'oobv_access':
            return f"{node['owner']}().{node['field']}"
        raise self.PLSyntaxError(f"cant express bruh: {node}")

    def _gen_owner(self, stmt):
        return f"class {stmt['name']}:\n    pass"
    
    def _gen_oobv(self, stmt):
        owner = stmt['owner']
        field = stmt['field']
        value = self._expr(stmt['value'])
        return f"setattr({owner}, {field!r}, {value})"

    def _oobv_set(self, owner_name, field, vartype, value):
        import sys
        ns = sys._getframe(2).f_globals
        cls = ns.get(owner_name)
        if cls is None:
            raise self.PLDLLError(f"owner {owner_name} not defined ahhh")
        setattr(cls, field, value)

    _import_stack = []
    _import_cache = {}
    
    def _gen_import(self, stmt):
        name = stmt['name']
        path = stmt['path'] or f"{name}.pf"
    
        if path in PufferLang._import_stack:
            raise self.PLDLLError(f"circular import: {path}")
        if path in PufferLang._import_cache:
            return PufferLang._import_cache[path]
        if not os.path.exists(path):
            raise self.PLDLLError(f"cannot find: {path}")
    
        PufferLang._import_stack.append(path)
        try:
            with open(path, 'r') as f:
                source = f.read()
            sub = PufferLang(source, mode='pdl' if path.endswith('.pdl') else 'pf')
            sub.compile()
            out = (
                f"# === imported from {path} ===\n"
                f"{sub.py_code}\n"
                f"# === end import {name} ===\n"
            )
            PufferLang._import_cache[path] = out
            return out
        finally:
            PufferLang._import_stack.pop()

    def _gen_funcdef(self, stmt):
        params = ', '.join(stmt['params'])
        lines = [f"def {stmt['name']}({params}):"]
        body_code = []
        for s in stmt['body']:
            body_code.append(self._gen_stmt(s))
        if not body_code:
            body_code = ['pass']
        for line in body_code:
            lines.append('    ' + line)
        return '\n'.join(lines)

    def compile(self):
        self.lex()
        self.parse()
        self.codegen()
        return self.py_code

    def run(self, show_code=True):
        self.compile()
        if show_code:
            print("=== interpreted ===")
            print(self.py_code)
            print("=== result ===")
        exec(self.py_code, {'_oobv_set': self._oobv_set})

def compilepl(file):
    with open(file, "r") as f:
        source = f.read()
    mode = 'pdl' if file.endswith('.pdl') else 'pf'
    PufferLang(source, mode=mode).run()