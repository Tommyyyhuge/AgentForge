"""
AgentForge 安全数学计算器工具模块

提供基于 AST 的安全数学表达式计算功能。
不支持 eval/exec，仅支持纯数学运算。
"""
import ast
import logging
import math
import operator
from typing import Any, Dict, Union

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 安全运算支持的操作符映射
_ALLOWED_OPERATORS: Dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# 允许的常量类型
_ALLOWED_CONSTANTS: tuple = (int, float)

# 允许的数学函数映射（安全子集）
_ALLOWED_FUNCTIONS: Dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "pow": pow,
}


class CalculatorSecurityError(Exception):
    """计算器安全异常 - 检测到不安全的表达式"""

    pass


class CalculatorTool(BaseTool):
    """安全数学计算器工具

    基于 Python AST 模块实现安全的数学表达式计算。
    仅支持基本算术运算和有限的安全数学函数，避免任意代码执行风险。

    支持的操作:
        - 基本运算: +, -, *, /, ** (幂)
        - 括号分组: (, )
        - 安全函数: abs(), round(), min(), max(), sqrt()
        - 整数和浮点数常量
    """

    name: str = "calculator"
    description: str = (
        "安全的数学计算器，支持基本算术运算（+、-、*、/、**）和"
        "安全数学函数（abs、round、min、max、sqrt）"
    )
    version: str = "1.0"

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义计算器工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "expression": {
                    "type": "string",
                    "description": (
                        "要计算的数学表达式。支持的运算: +, -, *, /, **, (, )。"
                        "支持的安全函数: abs, round, min, max, sqrt。"
                        "示例: '2 + 3 * 4'、'(1 + 2) * 3'、'sqrt(16) + 2**3'"
                    ),
                },
            },
            required=["expression"],
            examples=[
                {"expression": "2 + 3 * 4"},
                {"expression": "(1 + 2) * 3"},
                {"expression": "2 ** 10"},
                {"expression": "sqrt(16) + round(3.7)"},
            ],
        )

    def _safe_eval_node(self, node: ast.AST) -> Union[int, float]:
        """安全地递归计算 AST 节点

        仅处理白名单中的节点类型，拒绝任何不安全操作。

        Args:
            node: AST 语法树节点

        Returns:
            计算结果（int 或 float）

        Raises:
            CalculatorSecurityError: 遇到不支持的节点类型时抛出
        """
        # 数值常量
        if isinstance(node, ast.Constant):
            value = node.value
            if not isinstance(value, _ALLOWED_CONSTANTS):
                raise CalculatorSecurityError(
                    f"不支持的常量类型: {type(value).__name__}，"
                    f"仅支持 int 和 float"
                )
            return value

        # 二元运算 (+, -, *, /, **)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_OPERATORS:
                raise CalculatorSecurityError(
                    f"不支持的运算符: {type(node.op).__name__}"
                )
            left = self._safe_eval_node(node.left)
            right = self._safe_eval_node(node.right)
            return _ALLOWED_OPERATORS[op_type](left, right)

        # 一元运算 (+, - 前缀)
        if isinstance(node, ast.UnaryOp):
            op_type_unary: type[ast.unaryop] = type(node.op)  # type: ignore[assignment]
            if op_type_unary not in _ALLOWED_OPERATORS:
                raise CalculatorSecurityError(
                    f"不支持的一元运算符: {type(node.op).__name__}"
                )
            operand = self._safe_eval_node(node.operand)
            return _ALLOWED_OPERATORS[op_type_unary](operand)

        # 函数调用（允许的安全函数子集）
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise CalculatorSecurityError("仅支持命名函数调用")
            func_name = node.func.id
            if func_name not in _ALLOWED_FUNCTIONS:
                raise CalculatorSecurityError(
                    f"不支持的函数: {func_name}()，"
                    f"允许: {', '.join(sorted(_ALLOWED_FUNCTIONS.keys()))}"
                )
            # 计算函数参数
            args = [self._safe_eval_node(arg) for arg in node.args]
            try:
                return _ALLOWED_FUNCTIONS[func_name](*args)
            except (ValueError, ZeroDivisionError) as e:
                raise CalculatorSecurityError(f"函数 {func_name}() 执行错误: {e}")

        # 所有其他节点类型均拒绝
        raise CalculatorSecurityError(
            f"不支持的表达式节点: {type(node).__name__}。"
            f"仅支持基本算术运算和安全函数。"
        )

    def _evaluate_expression(self, expression: str) -> Union[int, float]:
        """解析并安全计算表达式

        Args:
            expression: 数学表达式字符串

        Returns:
            计算结果

        Raises:
            CalculatorSecurityError: 表达式不安全或解析失败时抛出
        """
        # 空表达式检查
        if not expression or not expression.strip():
            raise CalculatorSecurityError("表达式不能为空")

        expression = expression.strip()

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise CalculatorSecurityError(f"表达式语法错误: {e}")

        # 验证顶层节点：必须是 Expression(body=...)
        if not isinstance(tree, ast.Expression):
            raise CalculatorSecurityError("表达式格式无效")

        return self._safe_eval_node(tree.body)

    async def execute(self, **kwargs) -> str:
        """执行数学表达式计算

        Args:
            **kwargs: 工具参数，包含:
                - expression: 要计算的数学表达式字符串

        Returns:
            计算结果字符串，格式为 "结果: <value>"，
            或在错误时返回 "[计算错误] <信息>"
        """
        expression: str = kwargs.get("expression", "")

        logger.info("calculator 接收表达式: %s", expression)

        try:
            result = self._evaluate_expression(expression)

            # 格式化输出：整数不显示小数点
            if isinstance(result, float) and result == int(result):
                result = int(result)

            logger.info("calculator 计算结果: %s = %s", expression, result)
            return f"结果: {result}"

        except CalculatorSecurityError as e:
            logger.warning("calculator 安全错误: %s", e)
            return f"[计算错误] {e}"
        except ZeroDivisionError:
            logger.warning("calculator 除零错误: %s", expression)
            return "[计算错误] 除数不能为零"
        except OverflowError:
            logger.warning("calculator 溢出错误: %s", expression)
            return "[计算错误] 计算结果溢出"
        except Exception as e:
            logger.error("calculator 未知错误: %s", e)
            return f"[计算错误] 计算失败: {e}"

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的模式定义（字典格式）

        Returns:
            包含工具元数据和参数定义的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            **self.schema.model_dump(),
        }
