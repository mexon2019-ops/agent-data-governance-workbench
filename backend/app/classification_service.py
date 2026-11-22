"""Rule-based metadata field classification suggestions.

Suggestions are based only on column names and declared data types.
No source database rows are read or sampled.
"""
import re


HIGH_PATTERNS = [
    (r"password|passwd|secret|api[_-]?key|access[_-]?token", "疑似认证凭据字段"),
    (r"id[_-]?card|identity[_-]?(no|number)|national[_-]?id|身份证|证件号码", "疑似个人身份标识字段"),
    (r"bank[_-]?card|card[_-]?no|bank[_-]?account|银行卡|银行账号", "疑似金融账户标识字段"),
    (r"salary|payroll|薪资|工资|生物识别|指纹|人脸", "疑似高度敏感个人信息字段"),
]
SENSITIVE_PATTERNS = [
    (r"phone|mobile|tel|telephone|email|mail|手机号|电话|邮箱", "疑似联系方式字段"),
    (r"address|addr|住址|地址|联系人|contact", "疑似联系地址或联系人字段"),
    (r"customer[_-]?name|supplier[_-]?name|employee[_-]?name|real[_-]?name|姓名|客户名称|供应商名称|员工姓名", "疑似个人姓名字段"),
    (r"tax[_-]?(no|id)|social[_-]?credit|统一社会信用代码|纳税人识别号", "疑似税务或主体身份标识字段"),
    (r"account[_-]?no|account[_-]?number|账号", "疑似账户标识字段"),
]


def suggest_field_classification(column_name: str, data_type: str = "") -> dict:
    name = (column_name or "").strip().lower()
    for pattern, reason in HIGH_PATTERNS:
        if re.search(pattern, name, flags=re.IGNORECASE):
            return {"suggested_level": "高度敏感", "basis": reason, "confidence": "高"}
    for pattern, reason in SENSITIVE_PATTERNS:
        if re.search(pattern, name, flags=re.IGNORECASE):
            return {"suggested_level": "敏感", "basis": reason, "confidence": "中"}
    if re.search(r"(^|[_-])(id|uuid|guid|code|no|number)([_-]|$)", name):
        return {"suggested_level": "内部", "basis": "疑似业务标识字段，需结合业务用途确认", "confidence": "低"}
    return {
        "suggested_level": "未分级",
        "basis": "字段名称未命中内置敏感特征；需由数据责任人结合业务含义确认",
        "confidence": "低",
    }
