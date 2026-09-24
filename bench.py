"""性能基准：规则从十几条扩到上万条，验证单条记录校验接近线性，
且编译只发生一次。

对比三种写法：
  A. CompiledRuleSet（编译一次，复用多次）—— 推荐用法
  B. 每条记录重新 CompiledRuleSet(...) —— 反面教材：重复编译
  C. naive_validate（不编译，逐条解释，正则每次现编译）—— 重构前常见写法

运行: python3 bench.py
"""
import random
import time

from validator import CompiledRuleSet, naive_validate

N_RECORDS = 2000          # A 用的记录数
N_RECORDS_SLOW = 100      # B / C 太慢，用较少记录


def make_rules(n_rules, n_fields, rng):
    """生成 n_rules 条无冲突规则，分布在 n_fields 个字段上。"""
    fields = ['f%04d' % i for i in range(n_fields)]
    schema = {f: 'any' for f in fields}
    rules = []
    counters = {f: [0, 0, 0] for f in fields}  # 每字段各类型计数，保证参数唯一
    while len(rules) < n_rules:
        field = fields[rng.randrange(n_fields)]
        kind = len(rules) % 3
        n = counters[field][kind]
        counters[field][kind] += 1
        if kind == 0:  # 唯一正则，避免重复规则
            rules.append({'field': field, 'check': 'regex',
                          'param': '^[a-z0-9]{%d,}$' % (n + 1),
                          'code': 'E_FORMAT', 'msg': '%s 格式不正确' % field})
        elif kind == 1:  # min_length 全部 < 1000
            rules.append({'field': field, 'check': 'min_length',
                          'param': n,
                          'code': 'E_LENGTH_MIN', 'msg': '%s 太短' % field})
        else:  # max_length 全部 >= 1000，与 min_length 不冲突
            rules.append({'field': field, 'check': 'max_length',
                          'param': 1000 + n,
                          'code': 'E_LENGTH_MAX', 'msg': '%s 太长' % field})
    return schema, rules


def make_records(n, fields, rng):
    return [{f: 'v' * rng.randint(0, 150) for f in fields} for _ in range(n)]


def bench():
    rng = random.Random(20260924)
    print('%-8s %-10s %-14s %-16s %-18s %s'
          % ('规则数', '编译一次(ms)', 'A: 编译一次复用', 'B: 每条重新编译',
             'C: 朴素逐条解释', 'A 吞吐(条/秒)'))
    print('-' * 96)
    for n_rules in (16, 100, 1000, 10000):
        n_fields = max(8, n_rules // 10)
        schema, rules = make_rules(n_rules, n_fields, rng)
        fields = list(schema)
        records = make_records(N_RECORDS, fields, rng)

        # A: 编译一次
        t0 = time.perf_counter()
        engine = CompiledRuleSet(rules, schema)
        compile_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for rec in records:
            engine.validate(rec)
        a_total = time.perf_counter() - t0
        a_per_rec_us = a_total / N_RECORDS * 1e6
        a_qps = N_RECORDS / a_total

        # B / C 仅在规则数不大时实测，否则按耗时外推跳过
        if n_rules <= 1000:
            slow_records = records[:N_RECORDS_SLOW]
            t0 = time.perf_counter()
            for rec in slow_records:
                CompiledRuleSet(rules, schema).validate(rec)
            b_per_rec_us = (time.perf_counter() - t0) / N_RECORDS_SLOW * 1e6

            t0 = time.perf_counter()
            for rec in slow_records:
                naive_validate(rules, rec)
            c_per_rec_us = (time.perf_counter() - t0) / N_RECORDS_SLOW * 1e6
            b_str = '%.1f us' % b_per_rec_us
            c_str = '%.1f us' % c_per_rec_us
        else:
            b_str = '过慢，跳过(>分钟级)'
            c_str = '过慢，跳过(>分钟级)'

        print('%-8d %-10.2f %-16s %-18s %-18s %.0f'
              % (n_rules, compile_ms, '%.1f us' % a_per_rec_us, b_str, c_str,
                 a_qps))

    print()
    print('说明: A 列为单条记录平均耗时（编译成本已在“编译一次”列单独列出，')
    print('不摊入每条记录）；B 列把编译放进每条记录的循环，是典型错误用法。')


if __name__ == '__main__':
    bench()
