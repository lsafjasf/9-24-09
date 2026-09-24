"""规则冲突检测样例：演示加载时自检如何报错并指出规则序号。

运行: python3 conflict_demo.py
"""
from rules_full import SCHEMA
from validator import CompiledRuleSet, RuleSetError


def _r(field, check, param=None, code='E_X', msg='m'):
    rule = {'field': field, 'check': check, 'code': code, 'msg': msg}
    if param is not None:
        rule['param'] = param
    return rule


CASES = {
    '互斥规则冲突（长度）': [
        _r('username', 'min_length', 10),
        _r('username', 'max_length', 5),     # 与 #0 互斥：任何值都无法通过
    ],
    '互斥规则冲突（数值范围）': [
        _r('age', 'min', 100),
        _r('age', 'max', 50),                # 与 #0 互斥
        _r('age', 'min', 0),                 # 合法，不应被误报
    ],
    '要求了不存在的字段': [
        _r('username', 'required'),
        _r('ghost_field', 'min_length', 3),  # 字段不存在
    ],
    '参数越界': [
        _r('username', 'min_length', -1),    # 负数长度
        _r('email', 'regex', '(['),          # 正则无法编译
        _r('age', 'type', 'dict'),           # 非法类型参数
    ],
    '重复规则': [
        _r('score', 'min', 0),
        _r('score', 'min', 0),               # 与 #0 完全重复
    ],
    '枚举与范围互斥': [
        _r('score', 'enum', (1, 2, 3)),
        _r('score', 'min', 10),              # 枚举值全部 < 10
    ],
}


def main():
    for title, rules in CASES.items():
        print('=== %s ===' % title)
        try:
            CompiledRuleSet(rules, SCHEMA)
            print('  通过（不应发生）')
        except RuleSetError as exc:
            for problem in exc.problems:
                print('  ' + problem)
        print()


if __name__ == '__main__':
    main()
