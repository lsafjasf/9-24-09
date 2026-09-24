"""差分测试：证明重构前后行为等价。

两层对照：
  1. 固定规则表 vs if 分支旧代码：随机生成记录，legacy_validator 与
     CompiledRuleSet 对同一输入的结论与错误列表逐条一致。
  2. 随机规则表 vs 朴素参考实现：随机生成规则与记录，CompiledRuleSet
     与 naive_validate（不编译的独立解释器）逐条一致，证明“编译一次”
     的优化不改变语义。
另含规则表自检（冲突检测）的单元测试。

运行: python3 test_differential.py  （或 python3 -m unittest -v）
"""
import random
import unittest

from legacy_validator import validate_record as legacy_validate
from rules_full import SCHEMA, RULES
from validator import CompiledRuleSet, RuleSetError, check_rules, naive_validate

ENGINE = CompiledRuleSet(RULES, SCHEMA)

# 每个字段的候选值：合法值、边界值、非法值、错误类型混在一起
CANDIDATES = {
    'username': ['abc', 'ab', 'a' * 20, 'a' * 21, 'valid_name1', 'has space',
                 '', 123, None, '汉字名', 'ok_123', 'a-b'],
    'password': ['12345678', 'short', 'x' * 64, 'x' * 65, '', 12345678, None],
    'name': ['张三', '', 'n' * 50, 'n' * 51, 7, None],
    'age': [0, 150, 151, -1, 30, '30', 3.5, True, None],
    'gender': ['male', 'female', 'other', 'M', '', 0, None],
    'email': ['a@b.com', 'bad-email', 'a@b', '', 42, None, 'x+y@z.co'],
    'phone': ['13812345678', '12345678901', '1381234567', '', 13812345678, None],
    'id_card': ['1' * 17 + 'X', '1' * 18, '123', '', 0, None],
    'birthday': ['2024-01-01', '2024-13-01', '2024-1-1', 'not-a-date', '', 0, None],
    'zipcode': ['100000', '12345', '1234567', 'abcdef', '', 100000, None],
    'salary': [0, 10000000, 10000001, -1, 5000.5, '5000', True, None],
    'score': [0, 100, 100.5, 101, -0.1, '90', False, None],
    'website': ['http://a.com', 'https://b.cn/x', 'ftp://c', '', 1, None],
    'ip': ['1.2.3.4', '256.1.1.1', '1.2.3', 'a.b.c.d', '', 0, None],
    'amount': [0, 0.01, -1, 999999, '10', True, None],
}


def random_record(rng):
    record = {}
    for field, values in CANDIDATES.items():
        if rng.random() < 0.7:  # 30% 概率缺字段，覆盖必填/可选分支
            record[field] = rng.choice(values)
    return record


class TestLegacyEquivalence(unittest.TestCase):
    """重构前后对照：随机记录，错误列表逐条一致。"""

    def test_random_records(self):
        rng = random.Random(20260924)
        for i in range(5000):
            record = random_record(rng)
            expected = legacy_validate(record)
            actual = ENGINE.validate(record)
            self.assertEqual(
                expected, actual,
                '第 %d 条记录不一致\n记录: %r\n旧: %r\n新: %r'
                % (i, record, expected, actual))

    def test_boundary_records(self):
        # 显式构造全合法 / 全缺失 / 全错误类型三种极端记录
        full_ok = {
            'username': 'user_01', 'password': 'p' * 8, 'name': '张三',
            'age': 30, 'gender': 'male', 'email': 'a@b.com',
            'phone': '13812345678', 'id_card': '1' * 17 + 'X',
            'birthday': '2024-01-01', 'zipcode': '100000', 'salary': 1,
            'score': 100, 'website': 'http://a.com', 'ip': '1.2.3.4',
            'amount': 0,
        }
        all_wrong_type = {f: object() for f in CANDIDATES}
        all_wrong_type['gender'] = 'nope'
        for record in (full_ok, {}, all_wrong_type):
            self.assertEqual(legacy_validate(record), ENGINE.validate(record))


# ------------------------------------------------------------ 随机规则对照

VALUE_POOL = ['', 'a', 'abc', 'x' * 10, 'y' * 60, 0, 1, -5, 3.14, 100,
              True, False, None, '2024-01-01', 'bad', '1.2.3.4', ['x'],
              'a@b.com', '13812345678', '汉字']


def random_rules(rng, schema):
    """生成保证无冲突的随机规则表（同字段边界按构造保持一致）。"""
    rules = []
    for field in schema:
        used = set()

        def add(check, param=None):
            if check in used:
                return
            used.add(check)
            rule = {'field': field, 'check': check,
                    'code': 'E_' + check.upper(), 'msg': '%s %s' % (field, check)}
            if param is not None:
                rule['param'] = param
            rules.append(rule)

        if rng.random() < 0.5:
            add('required')
        if rng.random() < 0.5:
            add('type', rng.choice(['str', 'int', 'number']))
        if rng.random() < 0.4:
            lo = rng.randint(0, 5)
            add('min_length', lo)
            if rng.random() < 0.8:
                add('max_length', lo + rng.randint(0, 20))
        if rng.random() < 0.4:
            lo = rng.randint(-100, 0)
            add('min', lo)
            if rng.random() < 0.8:
                add('max', lo + rng.randint(0, 200))
        if rng.random() < 0.3:
            add('regex', rng.choice([r'^[a-z]+$', r'^\d{2,4}$', r'^x.*y$']))
        if rng.random() < 0.3:
            # 纯字符串枚举，避免与 min/max 数值规则产生“合法”的互斥
            add('enum', tuple(rng.sample(['red', 'green', 'blue', 'x', ''],
                                         rng.randint(1, 4))))
        if rng.random() < 0.2:
            add('date', '%Y-%m-%d')
    return rules


class TestRandomRulesEquivalence(unittest.TestCase):
    """随机规则 + 随机记录：编译执行 vs 朴素解释，逐条一致。"""

    def test_compiled_matches_naive(self):
        rng = random.Random(20260924)
        for trial in range(500):
            schema = {'f%d' % i: 'any'
                      for i in range(rng.randint(1, 10))}
            rules = random_rules(rng, schema)
            engine = CompiledRuleSet(rules, schema)  # 自检必须通过
            for _ in range(20):
                record = {f: rng.choice(VALUE_POOL) for f in schema
                          if rng.random() < 0.7}
                self.assertEqual(engine.validate(record),
                                 naive_validate(rules, record),
                                 'trial %d 规则 %r 记录 %r'
                                 % (trial, rules, record))


# ------------------------------------------------------------ 自检（冲突检测）

class TestRuleSelfCheck(unittest.TestCase):

    def assert_problem(self, rules, needle):
        problems = check_rules(rules, SCHEMA)
        self.assertTrue(any(needle in p for p in problems),
                        '未找到预期问题 %r，实际: %r' % (needle, problems))
        with self.assertRaises(RuleSetError):
            CompiledRuleSet(rules, SCHEMA)

    def base(self, field='username', check='required', **kw):
        rule = {'field': field, 'check': check,
                'code': 'E_X', 'msg': 'm'}
        rule.update(kw)
        return rule

    def test_unknown_field(self):
        rules = [self.base(), self.base(field='ghost')]
        self.assert_problem(rules, "规则 #1: 字段 'ghost' 不存在")

    def test_param_out_of_range(self):
        rules = [self.base(check='min_length', param=-1)]
        self.assert_problem(rules, '规则 #0: min_length 参数越界')
        rules = [self.base(check='regex', param='([')]
        self.assert_problem(rules, '规则 #0: 正则无法编译')
        rules = [self.base(check='type', param='dict')]
        self.assert_problem(rules, '规则 #0: type 参数越界')

    def test_length_conflict(self):
        rules = [self.base(check='min_length', param=10),
                 self.base(check='max_length', param=5)]
        self.assert_problem(rules, '规则 #0 与 #1')
        self.assert_problem(rules, '互斥')

    def test_range_conflict(self):
        rules = [self.base(field='age', check='min', param=100),
                 self.base(field='age', check='max', param=50)]
        self.assert_problem(rules, '规则 #0 与 #1')

    def test_duplicate_rule(self):
        rules = [self.base(check='min_length', param=3),
                 self.base(check='min_length', param=3)]
        self.assert_problem(rules, '重复规则')

    def test_enum_range_conflict(self):
        rules = [self.base(field='score', check='enum', param=(1, 2, 3)),
                 self.base(field='score', check='min', param=10)]
        self.assert_problem(rules, '枚举值全部落在')

    def test_canonical_rules_pass(self):
        self.assertEqual(check_rules(RULES, SCHEMA), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
