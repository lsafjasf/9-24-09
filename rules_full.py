"""规范规则表：与 legacy_validator.py 的 if 分支逐条等价。

*** 以后新增字段或规则，只需要改这一个文件 ***
  - 新增字段：在 SCHEMA 中登记字段名，并在 RULES 中追加该字段的规则；
  - 新增/修改规则：只改 RULES 列表；
  - 新增校验类型：才需要动 validator.py（在 CHECK_TYPES 与两个执行分支中
    各加一个分支），字段和规则的增删永远不需要动引擎。

规则顺序即错误输出顺序：字段按首次出现顺序，字段内按声明顺序，
与 legacy_validator.py 的分支顺序保持一致。
"""

# 已知字段登记表（加载自检时用于发现“要求了不存在的字段”）
SCHEMA = {
    'username': 'str', 'password': 'str', 'name': 'str', 'age': 'int',
    'gender': 'str', 'email': 'str', 'phone': 'str', 'id_card': 'str',
    'birthday': 'str', 'zipcode': 'str', 'salary': 'number',
    'score': 'number', 'website': 'str', 'ip': 'str', 'amount': 'number',
}


def _r(field, check, param, code, msg):
    rule = {'field': field, 'check': check, 'code': code, 'msg': msg}
    if param is not None:
        rule['param'] = param
    return rule


RULES = [
    # username: 必填, 字符串, 长度 3..20, 字母数字下划线
    _r('username', 'required', None, 'E_REQUIRED', 'username 为必填字段'),
    _r('username', 'type', 'str', 'E_TYPE', 'username 必须是字符串'),
    _r('username', 'min_length', 3, 'E_LENGTH_MIN', 'username 长度不能小于 3'),
    _r('username', 'max_length', 20, 'E_LENGTH_MAX', 'username 长度不能大于 20'),
    _r('username', 'regex', r'^[A-Za-z0-9_]+$', 'E_FORMAT',
       'username 只能包含字母、数字和下划线'),

    # password: 必填, 字符串, 长度 8..64
    _r('password', 'required', None, 'E_REQUIRED', 'password 为必填字段'),
    _r('password', 'type', 'str', 'E_TYPE', 'password 必须是字符串'),
    _r('password', 'min_length', 8, 'E_LENGTH_MIN', 'password 长度不能小于 8'),
    _r('password', 'max_length', 64, 'E_LENGTH_MAX', 'password 长度不能大于 64'),

    # name: 必填, 字符串, 长度 1..50
    _r('name', 'required', None, 'E_REQUIRED', 'name 为必填字段'),
    _r('name', 'type', 'str', 'E_TYPE', 'name 必须是字符串'),
    _r('name', 'min_length', 1, 'E_LENGTH_MIN', 'name 长度不能小于 1'),
    _r('name', 'max_length', 50, 'E_LENGTH_MAX', 'name 长度不能大于 50'),

    # age: 必填, 整数, 0..150
    _r('age', 'required', None, 'E_REQUIRED', 'age 为必填字段'),
    _r('age', 'type', 'int', 'E_TYPE', 'age 必须是整数'),
    _r('age', 'min', 0, 'E_RANGE_MIN', 'age 不能小于 0'),
    _r('age', 'max', 150, 'E_RANGE_MAX', 'age 不能大于 150'),

    # gender: 必填, 枚举
    _r('gender', 'required', None, 'E_REQUIRED', 'gender 为必填字段'),
    _r('gender', 'enum', ('male', 'female', 'other'), 'E_ENUM',
       'gender 只能是 male/female/other'),

    # email: 必填, 字符串, 格式
    _r('email', 'required', None, 'E_REQUIRED', 'email 为必填字段'),
    _r('email', 'type', 'str', 'E_TYPE', 'email 必须是字符串'),
    _r('email', 'regex', r'^[\w.+-]+@[\w-]+\.[\w.]+$', 'E_FORMAT',
       'email 格式不正确'),

    # phone: 可选, 字符串, 手机号格式
    _r('phone', 'type', 'str', 'E_TYPE', 'phone 必须是字符串'),
    _r('phone', 'regex', r'^1[3-9]\d{9}$', 'E_FORMAT', 'phone 格式不正确'),

    # id_card: 可选, 字符串, 18 位身份证格式
    _r('id_card', 'type', 'str', 'E_TYPE', 'id_card 必须是字符串'),
    _r('id_card', 'regex', r'^\d{17}[\dXx]$', 'E_FORMAT', 'id_card 格式不正确'),

    # birthday: 可选, 字符串, YYYY-MM-DD
    _r('birthday', 'type', 'str', 'E_TYPE', 'birthday 必须是字符串'),
    _r('birthday', 'date', '%Y-%m-%d', 'E_FORMAT',
       'birthday 必须是 YYYY-MM-DD 格式'),

    # zipcode: 可选, 字符串, 6 位数字
    _r('zipcode', 'type', 'str', 'E_TYPE', 'zipcode 必须是字符串'),
    _r('zipcode', 'regex', r'^\d{6}$', 'E_FORMAT', 'zipcode 格式不正确'),

    # salary: 可选, 数字, 0..10000000
    _r('salary', 'type', 'number', 'E_TYPE', 'salary 必须是数字'),
    _r('salary', 'min', 0, 'E_RANGE_MIN', 'salary 不能小于 0'),
    _r('salary', 'max', 10000000, 'E_RANGE_MAX', 'salary 不能大于 10000000'),

    # score: 可选, 数字, 0..100
    _r('score', 'type', 'number', 'E_TYPE', 'score 必须是数字'),
    _r('score', 'min', 0, 'E_RANGE_MIN', 'score 不能小于 0'),
    _r('score', 'max', 100, 'E_RANGE_MAX', 'score 不能大于 100'),

    # website: 可选, 字符串, http(s) URL
    _r('website', 'type', 'str', 'E_TYPE', 'website 必须是字符串'),
    _r('website', 'regex', r'^https?://\S+$', 'E_FORMAT', 'website 格式不正确'),

    # ip: 可选, 字符串, IPv4
    _r('ip', 'type', 'str', 'E_TYPE', 'ip 必须是字符串'),
    _r('ip', 'regex', r'^(\d{1,3}\.){3}\d{1,3}$', 'E_FORMAT', 'ip 格式不正确'),

    # amount: 必填, 数字, >= 0
    _r('amount', 'required', None, 'E_REQUIRED', 'amount 为必填字段'),
    _r('amount', 'type', 'number', 'E_TYPE', 'amount 必须是数字'),
    _r('amount', 'min', 0, 'E_RANGE_MIN', 'amount 不能小于 0'),
]
