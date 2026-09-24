"""规则表驱动的统一校验器（重构后）。

核心思想：
  1. 规则声明与执行分离 —— 规则是纯数据（见 rules_full.py），本模块只做执行。
  2. 加载时自检 —— check_rules() 在编译前检查未知字段、参数越界、互斥规则冲突，
     所有问题都带规则序号，一次性报出。
  3. 编译一次、复用多次 —— CompiledRuleSet 在构造时完成自检、按字段分组、
     预编译正则，之后 validate() 对每条记录只做查表执行，不重复编译。

规则格式（dict）：
  field : 字段名（必须存在于 schema）
  check : required / type / min_length / max_length / min / max / regex / enum / date
  param : 参数（required 无参数；type 取 'str'/'int'/'number'）
  code  : 错误码，msg : 错误消息 —— 错误分类与消息语义由规则自带，引擎不解释。
"""
import re
from datetime import datetime

CHECK_TYPES = ('required', 'type', 'min_length', 'max_length',
               'min', 'max', 'regex', 'enum', 'date')
TYPE_PARAMS = ('str', 'int', 'number')

# 参数合法边界：超出即视为“参数越界”，加载时报错
MAX_LENGTH_PARAM = 1_000_000      # min_length / max_length 上限
MAX_PATTERN_LEN = 1_000           # 正则文本长度上限


class RuleSetError(ValueError):
    """规则表自检失败。problems 为带规则序号的问题列表。"""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__(
            '规则表自检失败（%d 处问题）:\n%s'
            % (len(self.problems), '\n'.join(self.problems)))


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_ok(value, param):
    if param == 'str':
        return isinstance(value, str)
    if param == 'int':
        return isinstance(value, int) and not isinstance(value, bool)
    if param == 'number':
        return _is_number(value)
    return False


# ---------------------------------------------------------------- 加载时自检

def check_rules(rules, schema):
    """返回问题列表（空列表表示通过）。每条问题都带规则序号 #i。"""
    problems = []
    usable = []  # 通过单条检查的 (index, rule)，用于跨规则冲突检测

    for i, rule in enumerate(rules):
        ok = True
        if not isinstance(rule, dict):
            problems.append('规则 #%d: 规则必须是 dict' % i)
            continue
        field = rule.get('field')
        check = rule.get('check')
        param = rule.get('param')

        if field not in schema:
            problems.append('规则 #%d: 字段 %r 不存在于 schema' % (i, field))
            ok = False
        if check not in CHECK_TYPES:
            problems.append('规则 #%d: 未知校验类型 %r' % (i, check))
            ok = False
        elif check == 'type':
            if param not in TYPE_PARAMS:
                problems.append('规则 #%d: type 参数越界，必须是 %r，得到 %r'
                                % (i, TYPE_PARAMS, param))
                ok = False
        elif check in ('min_length', 'max_length'):
            if (not isinstance(param, int) or isinstance(param, bool)
                    or not 0 <= param <= MAX_LENGTH_PARAM):
                problems.append('规则 #%d: %s 参数越界，必须是 [0, %d] 的整数，得到 %r'
                                % (i, check, MAX_LENGTH_PARAM, param))
                ok = False
        elif check in ('min', 'max'):
            if not _is_number(param):
                problems.append('规则 #%d: %s 参数越界，必须是数字，得到 %r'
                                % (i, check, param))
                ok = False
        elif check == 'regex':
            if not isinstance(param, str) or not 1 <= len(param) <= MAX_PATTERN_LEN:
                problems.append('规则 #%d: regex 参数越界，必须是长度 [1, %d] 的字符串'
                                % (i, MAX_PATTERN_LEN))
                ok = False
            else:
                try:
                    re.compile(param)
                except re.error as exc:
                    problems.append('规则 #%d: 正则无法编译: %s' % (i, exc))
                    ok = False
        elif check == 'enum':
            if not isinstance(param, (list, tuple)) or len(param) == 0:
                problems.append('规则 #%d: enum 参数越界，必须是非空列表' % i)
                ok = False
        elif check == 'date':
            if not isinstance(param, str) or not param:
                problems.append('规则 #%d: date 参数越界，必须是非空格式串' % i)
                ok = False
        if ok:
            usable.append((i, rule))

    # ---- 跨规则冲突：同一字段上的互斥规则 ----
    by_field = {}
    for i, rule in usable:
        by_field.setdefault(rule['field'], []).append((i, rule))

    for field, items in by_field.items():
        # 1) 完全重复的规则（同字段、同类型、同参数）
        seen = {}
        for i, rule in items:
            key = (rule['check'], repr(rule.get('param')))
            if key in seen:
                problems.append('规则 #%d 与 #%d: 字段 %r 上的重复规则（%s）'
                                % (seen[key], i, field, rule['check']))
            else:
                seen[key] = i

        # 2) 长度边界互斥：有效 min_length > 有效 max_length
        mins = [(r['param'], i) for i, r in items if r['check'] == 'min_length']
        maxs = [(r['param'], i) for i, r in items if r['check'] == 'max_length']
        if mins and maxs:
            lo, lo_i = max(mins)
            hi, hi_i = min(maxs)
            if lo > hi:
                problems.append('规则 #%d 与 #%d: 字段 %r 上 min_length=%d 与 '
                                'max_length=%d 互斥，任何值都无法通过'
                                % (lo_i, hi_i, field, lo, hi))

        # 3) 数值边界互斥：有效 min > 有效 max
        los = [(r['param'], i) for i, r in items if r['check'] == 'min']
        his = [(r['param'], i) for i, r in items if r['check'] == 'max']
        eff_lo = eff_hi = None
        if los and his:
            eff_lo, lo_i = max(los)
            eff_hi, hi_i = min(his)
            if eff_lo > eff_hi:
                problems.append('规则 #%d 与 #%d: 字段 %r 上 min=%r 与 max=%r '
                                '互斥，任何值都无法通过'
                                % (lo_i, hi_i, field, eff_lo, eff_hi))

        # 4) 枚举与数值范围互斥：枚举值全部落在 [min, max] 之外
        enums = [(i, r['param']) for i, r in items if r['check'] == 'enum']
        if enums and (los or his):
            lo = eff_lo if eff_lo is not None else (max(los)[0] if los else None)
            hi = eff_hi if eff_hi is not None else (min(his)[0] if his else None)
            for e_i, values in enums:
                nums = [x for x in values if _is_number(x)]
                if nums and not any(
                        (lo is None or x >= lo) and (hi is None or x <= hi)
                        for x in nums):
                    problems.append('规则 #%d: 字段 %r 的枚举值全部落在 '
                                    '[min, max] 范围之外，与数值规则互斥'
                                    % (e_i, field))
    return problems


# ---------------------------------------------------------------- 编译与执行

class CompiledRuleSet:
    """编译一次、复用多次的规则集。

    构造时完成：自检 -> 按字段分组（保持字段首次出现顺序与组内声明顺序，
    以保证错误列表顺序与 if 分支版一致）-> 预编译正则。
    validate() 对每条记录只做查表执行，不做任何编译。
    """

    def __init__(self, rules, schema):
        problems = check_rules(rules, schema)
        if problems:
            raise RuleSetError(problems)
        self.rule_count = len(rules)
        grouped = {}
        order = []
        for rule in rules:
            field = rule['field']
            if field not in grouped:
                grouped[field] = []
                order.append(field)
            extra = re.compile(rule['param']) if rule['check'] == 'regex' else None
            param = rule.get('param')
            if rule['check'] == 'enum':
                param = tuple(param)
            grouped[field].append(
                (rule['check'], param, rule['code'], rule['msg'], extra))
        self._fields = [(field, grouped[field]) for field in order]

    def validate(self, record):
        errors = []
        for field, checks in self._fields:
            if field not in record:
                for kind, _p, code, msg, _e in checks:
                    if kind == 'required':
                        errors.append((field, code, msg))
                continue
            value = record[field]
            for kind, param, code, msg, extra in checks:
                if kind == 'required':
                    continue
                if kind == 'type':
                    if not _type_ok(value, param):
                        errors.append((field, code, msg))
                elif kind == 'min_length':
                    if isinstance(value, str) and len(value) < param:
                        errors.append((field, code, msg))
                elif kind == 'max_length':
                    if isinstance(value, str) and len(value) > param:
                        errors.append((field, code, msg))
                elif kind == 'min':
                    if _is_number(value) and value < param:
                        errors.append((field, code, msg))
                elif kind == 'max':
                    if _is_number(value) and value > param:
                        errors.append((field, code, msg))
                elif kind == 'regex':
                    if isinstance(value, str) and not extra.match(value):
                        errors.append((field, code, msg))
                elif kind == 'enum':
                    if value not in param:
                        errors.append((field, code, msg))
                elif kind == 'date':
                    if isinstance(value, str):
                        try:
                            datetime.strptime(value, param)
                        except ValueError:
                            errors.append((field, code, msg))
        return errors


def naive_validate(rules, record):
    """朴素参考实现：不编译、不预处理，逐条解释规则。

    用途：1) 差分测试中作为独立参照，验证 CompiledRuleSet 的编译优化
           没有改变语义；2) 性能对比中模拟“每条记录重复编译”的写法。
    """
    by_field = {}
    order = []
    for rule in rules:
        field = rule['field']
        if field not in by_field:
            by_field[field] = []
            order.append(field)
        by_field[field].append(rule)

    errors = []
    for field in order:
        field_rules = by_field[field]
        if field not in record:
            for rule in field_rules:
                if rule['check'] == 'required':
                    errors.append((field, rule['code'], rule['msg']))
            continue
        value = record[field]
        for rule in field_rules:
            kind = rule['check']
            param = rule.get('param')
            if kind == 'required':
                continue
            if kind == 'type':
                if not _type_ok(value, param):
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'min_length':
                if isinstance(value, str) and len(value) < param:
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'max_length':
                if isinstance(value, str) and len(value) > param:
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'min':
                if _is_number(value) and value < param:
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'max':
                if _is_number(value) and value > param:
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'regex':
                if isinstance(value, str) and not re.match(param, value):
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'enum':
                if value not in param:
                    errors.append((field, rule['code'], rule['msg']))
            elif kind == 'date':
                if isinstance(value, str):
                    try:
                        datetime.strptime(value, param)
                    except ValueError:
                        errors.append((field, rule['code'], rule['msg']))
    return errors
