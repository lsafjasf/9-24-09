"""重构前的校验代码：十几个字段逐个 if 分支。

该文件是重构的对照基准，差分测试用它证明重构前后行为完全一致。
错误元组格式: (字段名, 错误码, 错误消息)，顺序即分支执行顺序。
"""
import re
from datetime import datetime


def validate_record(record):
    errors = []

    # username: 必填, 字符串, 长度 3..20, 字母数字下划线
    if 'username' not in record:
        errors.append(('username', 'E_REQUIRED', 'username 为必填字段'))
    else:
        v = record['username']
        if not isinstance(v, str):
            errors.append(('username', 'E_TYPE', 'username 必须是字符串'))
        else:
            if len(v) < 3:
                errors.append(('username', 'E_LENGTH_MIN', 'username 长度不能小于 3'))
            if len(v) > 20:
                errors.append(('username', 'E_LENGTH_MAX', 'username 长度不能大于 20'))
            if not re.match(r'^[A-Za-z0-9_]+$', v):
                errors.append(('username', 'E_FORMAT', 'username 只能包含字母、数字和下划线'))

    # password: 必填, 字符串, 长度 8..64
    if 'password' not in record:
        errors.append(('password', 'E_REQUIRED', 'password 为必填字段'))
    else:
        v = record['password']
        if not isinstance(v, str):
            errors.append(('password', 'E_TYPE', 'password 必须是字符串'))
        else:
            if len(v) < 8:
                errors.append(('password', 'E_LENGTH_MIN', 'password 长度不能小于 8'))
            if len(v) > 64:
                errors.append(('password', 'E_LENGTH_MAX', 'password 长度不能大于 64'))

    # name: 必填, 字符串, 长度 1..50
    if 'name' not in record:
        errors.append(('name', 'E_REQUIRED', 'name 为必填字段'))
    else:
        v = record['name']
        if not isinstance(v, str):
            errors.append(('name', 'E_TYPE', 'name 必须是字符串'))
        else:
            if len(v) < 1:
                errors.append(('name', 'E_LENGTH_MIN', 'name 长度不能小于 1'))
            if len(v) > 50:
                errors.append(('name', 'E_LENGTH_MAX', 'name 长度不能大于 50'))

    # age: 必填, 整数, 0..150
    if 'age' not in record:
        errors.append(('age', 'E_REQUIRED', 'age 为必填字段'))
    else:
        v = record['age']
        if not isinstance(v, int) or isinstance(v, bool):
            errors.append(('age', 'E_TYPE', 'age 必须是整数'))
        else:
            if v < 0:
                errors.append(('age', 'E_RANGE_MIN', 'age 不能小于 0'))
            if v > 150:
                errors.append(('age', 'E_RANGE_MAX', 'age 不能大于 150'))

    # gender: 必填, 枚举
    if 'gender' not in record:
        errors.append(('gender', 'E_REQUIRED', 'gender 为必填字段'))
    else:
        v = record['gender']
        if v not in ('male', 'female', 'other'):
            errors.append(('gender', 'E_ENUM', 'gender 只能是 male/female/other'))

    # email: 必填, 字符串, 格式
    if 'email' not in record:
        errors.append(('email', 'E_REQUIRED', 'email 为必填字段'))
    else:
        v = record['email']
        if not isinstance(v, str):
            errors.append(('email', 'E_TYPE', 'email 必须是字符串'))
        else:
            if not re.match(r'^[\w.+-]+@[\w-]+\.[\w.]+$', v):
                errors.append(('email', 'E_FORMAT', 'email 格式不正确'))

    # phone: 可选, 字符串, 手机号格式
    if 'phone' in record:
        v = record['phone']
        if not isinstance(v, str):
            errors.append(('phone', 'E_TYPE', 'phone 必须是字符串'))
        else:
            if not re.match(r'^1[3-9]\d{9}$', v):
                errors.append(('phone', 'E_FORMAT', 'phone 格式不正确'))

    # id_card: 可选, 字符串, 18 位身份证格式
    if 'id_card' in record:
        v = record['id_card']
        if not isinstance(v, str):
            errors.append(('id_card', 'E_TYPE', 'id_card 必须是字符串'))
        else:
            if not re.match(r'^\d{17}[\dXx]$', v):
                errors.append(('id_card', 'E_FORMAT', 'id_card 格式不正确'))

    # birthday: 可选, 字符串, YYYY-MM-DD
    if 'birthday' in record:
        v = record['birthday']
        if not isinstance(v, str):
            errors.append(('birthday', 'E_TYPE', 'birthday 必须是字符串'))
        else:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                errors.append(('birthday', 'E_FORMAT', 'birthday 必须是 YYYY-MM-DD 格式'))

    # zipcode: 可选, 字符串, 6 位数字
    if 'zipcode' in record:
        v = record['zipcode']
        if not isinstance(v, str):
            errors.append(('zipcode', 'E_TYPE', 'zipcode 必须是字符串'))
        else:
            if not re.match(r'^\d{6}$', v):
                errors.append(('zipcode', 'E_FORMAT', 'zipcode 格式不正确'))

    # salary: 可选, 数字, 0..10000000
    if 'salary' in record:
        v = record['salary']
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(('salary', 'E_TYPE', 'salary 必须是数字'))
        else:
            if v < 0:
                errors.append(('salary', 'E_RANGE_MIN', 'salary 不能小于 0'))
            if v > 10000000:
                errors.append(('salary', 'E_RANGE_MAX', 'salary 不能大于 10000000'))

    # score: 可选, 数字, 0..100
    if 'score' in record:
        v = record['score']
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(('score', 'E_TYPE', 'score 必须是数字'))
        else:
            if v < 0:
                errors.append(('score', 'E_RANGE_MIN', 'score 不能小于 0'))
            if v > 100:
                errors.append(('score', 'E_RANGE_MAX', 'score 不能大于 100'))

    # website: 可选, 字符串, http(s) URL
    if 'website' in record:
        v = record['website']
        if not isinstance(v, str):
            errors.append(('website', 'E_TYPE', 'website 必须是字符串'))
        else:
            if not re.match(r'^https?://\S+$', v):
                errors.append(('website', 'E_FORMAT', 'website 格式不正确'))

    # ip: 可选, 字符串, IPv4
    if 'ip' in record:
        v = record['ip']
        if not isinstance(v, str):
            errors.append(('ip', 'E_TYPE', 'ip 必须是字符串'))
        else:
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', v):
                errors.append(('ip', 'E_FORMAT', 'ip 格式不正确'))

    # amount: 必填, 数字, >= 0
    if 'amount' not in record:
        errors.append(('amount', 'E_REQUIRED', 'amount 为必填字段'))
    else:
        v = record['amount']
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(('amount', 'E_TYPE', 'amount 必须是数字'))
        else:
            if v < 0:
                errors.append(('amount', 'E_RANGE_MIN', 'amount 不能小于 0'))

    return errors
