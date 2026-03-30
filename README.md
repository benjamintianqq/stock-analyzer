# 股票买卖点分析小程序

基于《二级市场买卖点判断：顶级机构的系统性决策框架》
覆盖六大维度：基本面、技术面、市场结构、仓位风控、行为偏差、综合决策矩阵

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 美股
python analyzer.py --market US --ticker AAPL
python analyzer.py --market US --ticker TSLA
python analyzer.py --market US --ticker NVDA

# A股
python analyzer.py --market CN --ticker 600519.SS   # 贵州茅台（沪市加.SS）
python analyzer.py --market CN --ticker 000858.SZ   # 五粮液（深市加.SZ）
python analyzer.py --market CN --ticker 300750.SZ   # 宁德时代

# 港股
python analyzer.py --market HK --ticker 0700.HK     # 腾讯
python analyzer.py --market HK --ticker 9988.HK     # 阿里巴巴
```

## 输出内容（六大维度）

1. **基本面** — 逆向DCF隐含增长率、Bernstein四阶段判断、质量过滤器五道防线
2. **技术面** — 12-1月动量、RSI/MACD/布林带信号、均线趋势
3. **市场结构** — 美股/A股/港股差异化分析框架
4. **仓位风控** — ATR止损位、半Kelly仓位建议、正金字塔5-3-2加仓计划
5. **行为偏差** — 锚定效应检查、处置效应警示、Druckenmiller自检问题
6. **综合决策** — 买入10条checklist、卖出10条checklist、最终买/持/卖建议

## 注意事项

- 数据来源：Yahoo Finance（yfinance）
- 部分指标（内部人交易、暗池信号、北向资金等）无法自动获取，程序会标注"需人工确认"
- A股换手率、政策信号需结合实际判断
- **本程序仅供参考，不构成投资建议**
