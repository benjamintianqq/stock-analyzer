#!/usr/bin/env python3
"""
股票买卖点分析小程序
基于《二级市场买卖点判断：顶级机构的系统性决策框架》
用法：python analyzer.py --market US --ticker AAPL
     python analyzer.py --market CN --ticker 600519.SS
     python analyzer.py --market HK --ticker 0700.HK
"""

import argparse
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
    import numpy as np
    import pandas as pd
except ImportError:
    print("请先安装依赖：pip install yfinance numpy pandas")
    sys.exit(1)

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def safe_get(info, key, default=None):
    v = info.get(key, default)
    return v if v not in (None, "None", "", "N/A") else default

def fmt(val, decimals=2, pct=False, suffix=""):
    if val is None:
        return "N/A"
    if pct:
        return f"{val*100:.{decimals}f}%"
    return f"{val:.{decimals}f}{suffix}"

def signal(condition, true_str="✅", false_str="❌", na_str="⚠️ 需人工确认"):
    if condition is None:
        return na_str
    return true_str if condition else false_str

# ─────────────────────────────────────────────
# 数据获取
# ─────────────────────────────────────────────

def fetch_data(ticker: str):
    print(f"  正在获取 {ticker} 数据...")
    t = yf.Ticker(ticker)
    hist = t.history(period="2y")          # 2年日线
    info = t.info
    return t, hist, info

# ─────────────────────────────────────────────
# 一、基本面分析
# ─────────────────────────────────────────────

def analyze_fundamental(info, hist):
    print("\n" + "="*50)
    print("【一、基本面分析】")
    print("="*50)

    # --- 逆向 DCF ---
    print("\n📐 逆向DCF（隐含增长率 vs 可实现增长率）")
    price = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    fcf = safe_get(info, "freeCashflow")
    shares = safe_get(info, "sharesOutstanding")
    wacc = 0.09  # 默认WACC 9%（无法自动获取，保守估计）

    implied_growth = None
    if price and fcf and shares:
        fcf_per_share = fcf / shares
        # 简化逆向DCF：P = FCF_ps * (1+g) / (WACC - g)
        # 解方程：g = (P*WACC - FCF_ps) / (P + FCF_ps)
        implied_growth = (price * wacc - fcf_per_share) / (price + fcf_per_share)

    # 历史FCF增长（用收益增长代理）
    hist_eps_growth = safe_get(info, "earningsGrowth")
    revenue_growth = safe_get(info, "revenueGrowth")

    if implied_growth is not None:
        print(f"  当前股价：${fmt(price)}")
        print(f"  FCF/股：${fmt(fcf/shares if fcf and shares else None, 2)}")
        print(f"  隐含FCF增长率：{fmt(implied_growth, 1, pct=True)}")
        print(f"  历史EPS增长率：{fmt(hist_eps_growth, 1, pct=True)} (代理指标)")
        if implied_growth and hist_eps_growth:
            diff = implied_growth - hist_eps_growth
            status = "⚠️ 市场预期偏乐观" if diff > 0.05 else ("✅ 预期合理" if diff > -0.05 else "🟢 存在低估机会")
            print(f"  预期差（隐含-历史）：{fmt(diff, 1, pct=True)} → {status}")
            print(f"  警戒阈值：>5%高估风险，<-5%低估机会")
    else:
        print("  ⚠️ 无法计算逆向DCF（FCF数据缺失），需人工确认")

    # --- 盈利修正周期（Bernstein四阶段）---
    print("\n📊 Bernstein盈利修正周期（四阶段判断）")
    rec_trend = safe_get(info, "recommendationKey")
    target_price = safe_get(info, "targetMeanPrice")
    analyst_count = safe_get(info, "numberOfAnalystOpinions")

    if price and target_price:
        upside = (target_price - price) / price
        print(f"  分析师一致目标价：${fmt(target_price)} | 当前价：${fmt(price)}")
        print(f"  上行空间：{fmt(upside, 1, pct=True)} | 分析师数量：{analyst_count}")
        print(f"  分析师评级：{rec_trend or 'N/A'}")
        if upside > 0.20:
            stage = "第二阶段（情绪悲观+预期转升）→ 🟢 最佳买入区"
        elif upside > 0.05:
            stage = "第三阶段（盈利动量期）→ 🟡 可持有，注意顶部"
        elif upside > -0.05:
            stage = "第三/四阶段边界 → 🟡 需警惕盈利见顶"
        else:
            stage = "第四阶段（负面盈利惊喜）→ 🔴 聪明钱开始卖出"
        print(f"  判断：{stage}")
    else:
        print("  ⚠️ 分析师数据缺失，需人工确认盈利修正方向")

    # --- 质量过滤器 ---
    print("\n🔍 质量过滤器（五道防线）")
    roe = safe_get(info, "returnOnEquity")
    roa = safe_get(info, "returnOnAssets")
    operating_margins = safe_get(info, "operatingMargins")
    profit_margins = safe_get(info, "profitMargins")
    debt_to_equity = safe_get(info, "debtToEquity")
    current_ratio = safe_get(info, "currentRatio")
    quick_ratio = safe_get(info, "quickRatio")
    gross_margins = safe_get(info, "grossMargins")

    # 近3年营收趋势（从hist无法直接拿，用revenue_growth代理）
    print(f"  第一道·营收趋势：营收增长 {fmt(revenue_growth, 1, pct=True)} {signal(revenue_growth and revenue_growth > 0)}")
    print(f"  第二道·盈利质量：毛利率 {fmt(gross_margins, 1, pct=True)} | 营业利率 {fmt(operating_margins, 1, pct=True)} {signal(operating_margins and operating_margins > 0.10)}")
    print(f"  第三道·杠杆水平：债务/权益 {fmt(debt_to_equity, 1)} | 流动比率 {fmt(current_ratio, 2)} {signal(debt_to_equity and debt_to_equity < 200 and current_ratio and current_ratio > 1)}")
    print(f"  第四道·护城河：ROE {fmt(roe, 1, pct=True)} | ROA {fmt(roa, 1, pct=True)} {signal(roe and roe > 0.15)}")
    print(f"  第五道·资本配置：净利润率 {fmt(profit_margins, 1, pct=True)} {signal(profit_margins and profit_margins > 0.10)}")

    # PE估值
    pe = safe_get(info, "trailingPE")
    forward_pe = safe_get(info, "forwardPE")
    pb = safe_get(info, "priceToBook")
    ev_ebitda = safe_get(info, "enterpriseToEbitda")
    peg = safe_get(info, "pegRatio")
    print(f"\n📏 估值指标")
    print(f"  PE(TTM)：{fmt(pe, 1)} | 远期PE：{fmt(forward_pe, 1)} | PB：{fmt(pb, 2)}")
    print(f"  EV/EBITDA：{fmt(ev_ebitda, 1)} | PEG：{fmt(peg, 2)}")
    if peg:
        peg_signal = "🟢 强买入信号" if peg < 0.8 else ("✅ 合理估值" if peg < 1.2 else ("⚠️ 偏贵" if peg < 2.0 else "🔴 需谨慎"))
        print(f"  PEG信号：{peg_signal}（<0.8强买，~1.0合理，>2.0谨慎）")

    return {
        "implied_growth": implied_growth,
        "hist_growth": hist_eps_growth,
        "upside": (target_price - price) / price if price and target_price else None,
        "pe": pe,
        "pb": pb,
        "peg": peg,
        "roe": roe,
        "revenue_growth": revenue_growth,
    }

# ─────────────────────────────────────────────
# 二、量化/技术面信号
# ─────────────────────────────────────────────

def analyze_technical(hist):
    print("\n" + "="*50)
    print("【二、量化/技术面信号】")
    print("="*50)

    if hist.empty or len(hist) < 50:
        print("  ⚠️ 历史数据不足，无法计算技术指标")
        return {}

    close = hist["Close"]
    volume = hist["Volume"]
    high = hist["High"]
    low = hist["Low"]

    # --- 动量因子（12-1月，跳过最近1个月）---
    print("\n🚀 动量因子（Jegadeesh & Titman 12-1月）")
    if len(close) >= 252:
        momentum_12_1 = (close.iloc[-22] - close.iloc[-252]) / close.iloc[-252]
        print(f"  12-1月动量：{fmt(momentum_12_1, 1, pct=True)}", end=" ")
        if momentum_12_1 > 0.20:
            print("→ 🟢 强势动量（>20%）")
        elif momentum_12_1 > 0:
            print("→ 🟡 温和正动量")
        else:
            print("→ 🔴 负动量（动量因子看空）")
    else:
        momentum_12_1 = None
        print("  ⚠️ 数据不足（需252个交易日）")

    # --- RSI(14) ---
    print("\n📈 RSI(14)")
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_now = rsi.iloc[-1]
    print(f"  RSI：{fmt(rsi_now, 1)}", end=" ")
    if rsi_now < 30:
        print("→ 🟢 超卖（买入信号）")
    elif rsi_now > 70:
        print("→ 🔴 超买（卖出信号）")
    else:
        print("→ 🟡 中性区间")

    # --- MACD(12/26/9) ---
    print("\n📉 MACD(12/26/9)")
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    macd_now = macd_line.iloc[-1]
    signal_now = signal_line.iloc[-1]
    hist_now = histogram.iloc[-1]
    hist_prev = histogram.iloc[-2]
    cross = "金叉🟢" if (macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]) else \
            "死叉🔴" if (macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]) else \
            ("多头排列🟢" if macd_line.iloc[-1] > signal_line.iloc[-1] else "空头排列🔴")
    print(f"  MACD线：{fmt(macd_now, 3)} | 信号线：{fmt(signal_now, 3)} | 柱状：{fmt(hist_now, 3)}")
    print(f"  状态：{cross} | 柱状{'扩大📈' if hist_now > hist_prev else '收缩📉'}")

    # --- 布林带(20/2σ) ---
    print("\n📊 布林带(20期/2σ)")
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    price_now = close.iloc[-1]
    bb_pct = (price_now - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])  # 0-1
    bw = (upper - lower) / sma20  # 布林带宽度
    bw_pct = bw.rank(pct=True).iloc[-1]  # 当前宽度百分位
    print(f"  当前价：{fmt(price_now, 2)} | 上轨：{fmt(upper.iloc[-1], 2)} | 下轨：{fmt(lower.iloc[-1], 2)}")
    print(f"  价格位置：{fmt(bb_pct, 1, pct=True)}（0%=下轨,100%=上轨）", end=" ")
    if bb_pct < 0.2:
        print("→ 🟢 接近下轨，超卖区")
    elif bb_pct > 0.8:
        print("→ 🔴 接近上轨，超买区")
    else:
        print("→ 🟡 中轨区间")
    print(f"  带宽百分位：{fmt(bw_pct, 0, pct=True)}", end=" ")
    if bw_pct < 0.25:
        print("→ ⚡ 极度缩口（65-70%概率即将大幅突破）")

    # --- 均线趋势（50SMA / 200SMA）---
    print("\n📏 均线趋势")
    sma50 = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    print(f"  当前价 {fmt(price_now, 2)} vs 50SMA {fmt(sma50, 2)}", end=" ")
    print("→ 🟢 多头" if price_now > sma50 else "→ 🔴 空头")
    if sma200:
        print(f"  当前价 {fmt(price_now, 2)} vs 200SMA {fmt(sma200, 2)}", end=" ")
        print("→ 🟢 多头（长期）" if price_now > sma200 else "→ 🔴 空头（长期）")
        if sma50 > sma200:
            print("  金叉状态（50SMA > 200SMA）🟢")
        else:
            print("  死叉状态（50SMA < 200SMA）🔴")

    # --- ATR(14) for 风控 ---
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean().iloc[-1]

    return {
        "momentum_12_1": momentum_12_1,
        "rsi": rsi_now,
        "macd_cross": cross,
        "bb_pct": bb_pct,
        "price": price_now,
        "sma50": sma50,
        "sma200": sma200,
        "atr14": atr14,
    }

# ─────────────────────────────────────────────
# 三、市场结构适配
# ─────────────────────────────────────────────

def analyze_market_structure(market: str, info, tech_data):
    print("\n" + "="*50)
    print(f"【三、市场结构适配 — {market}】")
    print("="*50)

    sector = safe_get(info, "sector", "未知行业")
    industry = safe_get(info, "industry", "")
    print(f"\n  行业：{sector} / {industry}")

    # 行业类型判断 → 对应估值框架
    growth_sectors = ["Technology", "Healthcare", "Consumer Cyclical", "Communication Services"]
    cyclical_sectors = ["Basic Materials", "Energy", "Industrials", "Consumer Cyclical"]
    defensive_sectors = ["Utilities", "Consumer Defensive", "Real Estate", "Financial Services"]

    if sector in growth_sectors:
        stock_type = "成长股"
        valuation_framework = "PEG（<0.8强买）+ Rule of 40 + PEAD效应"
    elif sector in cyclical_sectors:
        stock_type = "周期股"
        valuation_framework = "PB-ROE周期位置（PB<1倍且有正ROE历史→买入）"
    else:
        stock_type = "价值/防御股"
        valuation_framework = "股息率（>3-4%）+ FCF Yield（>8-10%）+ PE均值回归"

    print(f"  行业类型：{stock_type}")
    print(f"  适用估值框架：{valuation_framework}")

    # 市场特有分析
    print(f"\n🌍 {market}市场特有信号")
    if market == "US":
        print("  核心逻辑：盈利驱动（PEAD效应）")
        print("  关键观察：")
        print("  • 期权市场：当前无法自动获取隐含波动率偏斜，⚠️ 需人工查看 options chain")
        print("  • PEAD效应：科技股盈利超预期>10%有72%概率维持较高价格（关注下次财报）")
        print("  • ETF资金流：⚠️ 需人工确认（可查 ETF.com 或 Bloomberg）")
        beta = safe_get(info, "beta")
        if beta:
            print(f"  • Beta：{fmt(beta, 2)}（市场敏感度，>1放大市场波动）")

    elif market == "CN":
        print("  核心逻辑：政策驱动 + 情绪极端")
        print("  关键观察（需人工确认）：")
        print("  ⚠️ 换手率：<1%可能为底部信号；>10%主力介入；>45%极端投机")
        print("  ⚠️ 北向资金（季度汇总）：2024年起不再实时披露")
        print("  ⚠️ A股Bernstein四阶段：需结合社融M1数据判断政策底")
        print("  • 招商证券框架：阶段一（政策底）→ 阶段二（盈利加速）→ 阶段三（过热）")

    elif market == "HK":
        print("  核心逻辑：流动性折价 + 南向资金重定价")
        print("  关键观察（需人工确认）：")
        print("  ⚠️ AH溢价指数：>140-150%时H股倾向跑赢；降至<125%时A股可能追赶")
        print("  ⚠️ 南向资金：2025年日均流入63亿港元，南向占比35-40%（已成边际定价者）")
        print("  • 港股股息率注意：通过港股通需扣20%股息税（净收益率约打八折）")

    return {"stock_type": stock_type}

# ─────────────────────────────────────────────
# 四、仓位管理与风控
# ─────────────────────────────────────────────

def analyze_risk_management(tech_data, fund_data):
    print("\n" + "="*50)
    print("【四、仓位管理与风控建议】")
    print("="*50)

    price = tech_data.get("price")
    atr14 = tech_data.get("atr14")
    rsi = tech_data.get("rsi")
    upside = fund_data.get("upside")

    # ATR止损
    print("\n🛡️ ATR止损位建议（2倍ATR，波段交易标准）")
    if price and atr14:
        stop_loss_2atr = price - 2 * atr14
        stop_loss_3atr = price - 3 * atr14
        pct_2atr = atr14 * 2 / price
        print(f"  ATR(14)：{fmt(atr14, 2)}")
        print(f"  2倍ATR止损位：{fmt(stop_loss_2atr, 2)}（距现价 -{fmt(pct_2atr, 1, pct=True)}）← 波段推荐")
        print(f"  3倍ATR止损位：{fmt(stop_loss_3atr, 2)}（距现价 -{fmt(atr14*3/price, 1, pct=True)}）← 趋势交易")
        print(f"  原则：止损设在交易逻辑被否定的位置，不超过仓位价值的10%")
    else:
        print("  ⚠️ 数据不足，无法计算ATR止损")

    # Kelly仓位（简化版）
    print("\n💰 仓位建议（半Kelly法则）")
    if upside and price and atr14:
        # 简化Kelly：假设胜率55%（Bernstein第二阶段历史胜率56%）
        win_rate = 0.55
        reward = upside  # 目标上行
        risk = atr14 * 2 / price  # 2倍ATR止损
        if risk > 0:
            kelly_f = win_rate - (1 - win_rate) / (reward / risk)
            half_kelly = max(0, kelly_f * 0.5)
            print(f"  参数：胜率55%（Bernstein第二阶段）| 潜在回报 {fmt(upside, 1, pct=True)} | 止损 {fmt(risk, 1, pct=True)}")
            print(f"  全Kelly：{fmt(kelly_f, 1, pct=True)} | 半Kelly（推荐）：{fmt(half_kelly, 1, pct=True)}")
            if half_kelly < 0.02:
                print("  ⚠️ Kelly值极低，风险收益比不佳，建议观望")
            elif half_kelly > 0.20:
                print("  ⚠️ 理论仓位较高，机构通常单仓上限10%，集中型上限30%")
            else:
                print(f"  建议初始仓位：{fmt(half_kelly*0.5, 1, pct=True)}（首批），总计不超过{fmt(half_kelly, 1, pct=True)}")
    else:
        print("  ⚠️ 需要目标价和ATR数据才能计算Kelly仓位")

    # 正金字塔加仓
    print("\n📐 正金字塔加仓计划（5-3-2模型）")
    print("  第一批：50%目标仓位（初始买入，价格确认时）")
    print("  第二批：30%目标仓位（突破关键阻力位后）")
    print("  第三批：20%目标仓位（趋势明确加速时）")
    print("  规则：每次加仓必须<初始仓位；止损设在当前与前一入场价中点；最多连续加3次")

# ─────────────────────────────────────────────
# 五、行为偏差提醒
# ─────────────────────────────────────────────

def analyze_behavioral(hist, info):
    print("\n" + "="*50)
    print("【五、行为偏差提醒】")
    print("="*50)

    if hist.empty:
        print("  ⚠️ 数据不足")
        return

    close = hist["Close"]
    price_now = close.iloc[-1]
    high_52w = close.rolling(252).max().iloc[-1] if len(close) >= 252 else close.max()
    low_52w = close.rolling(252).min().iloc[-1] if len(close) >= 252 else close.min()
    pct_from_high = (price_now - high_52w) / high_52w
    pct_from_low = (price_now - low_52w) / low_52w

    print("\n⚓ 锚定效应检查")
    print(f"  52周高点：{fmt(high_52w, 2)} | 距高点：{fmt(pct_from_high, 1, pct=True)}")
    print(f"  52周低点：{fmt(low_52w, 2)} | 距低点：{fmt(pct_from_low, 1, pct=True)}")
    if pct_from_high > -0.05:
        print("  ⚠️ 接近52周高点！注意锚定效应——投资者在价格接近高点时往往反应不足")
    if pct_from_low < 0.20:
        print("  💡 接近52周低点区域，注意区分低估机会与价值陷阱")

    # 处置效应（近期涨跌幅）
    print("\n🧠 处置效应风险")
    ret_1m = (close.iloc[-1] - close.iloc[-22]) / close.iloc[-22] if len(close) >= 22 else None
    ret_3m = (close.iloc[-1] - close.iloc[-66]) / close.iloc[-66] if len(close) >= 66 else None
    print(f"  近1个月涨跌：{fmt(ret_1m, 1, pct=True)}")
    print(f"  近3个月涨跌：{fmt(ret_3m, 1, pct=True)}")
    if ret_1m and ret_1m > 0.15:
        print("  ⚠️ 近期大幅上涨——警惕'处置效应'：不要因浮盈就急于卖出赢家（Odean研究：被卖出的赢家随后12月跑赢持有标的约3.5%）")
    if ret_1m and ret_1m < -0.15:
        print("  ⚠️ 近期大幅下跌——警惕'损失厌恶'：不要为挽回损失增加风险暴露")

    # Druckenmiller自检问题
    print("\n🎯 Druckenmiller自检")
    print("  「假如我今天不持有这只股票，以当前价格我会买入吗？」")
    print("  如果答案是否定的，那持有它的理由是什么？是真实的价值判断，还是锚定偏差？")
    print("  「我不关心买入成本——它与未来的投资决策完全无关。」—— Druckenmiller")

# ─────────────────────────────────────────────
# 六、综合决策矩阵
# ─────────────────────────────────────────────

def final_decision(market, fund_data, tech_data, market_data):
    print("\n" + "="*50)
    print("【六、综合决策矩阵】")
    print("="*50)

    implied_growth = fund_data.get("implied_growth")
    hist_growth = fund_data.get("hist_growth")
    upside = fund_data.get("upside")
    pe = fund_data.get("pe")
    pb = fund_data.get("pb")
    peg = fund_data.get("peg")
    roe = fund_data.get("roe")
    revenue_growth = fund_data.get("revenue_growth")

    rsi = tech_data.get("rsi")
    momentum = tech_data.get("momentum_12_1")
    macd_cross = tech_data.get("macd_cross", "")
    price = tech_data.get("price")
    sma50 = tech_data.get("sma50")
    sma200 = tech_data.get("sma200")

    score_buy = 0
    score_sell = 0

    print("\n✅ 买入Checklist（顶级机构10条标准）")
    checks_buy = [
        ("逆向DCF：隐含增长率<可实现增长率，存在预期差",
         (implied_growth and hist_growth and (implied_growth - hist_growth) < 0.05) if (implied_growth and hist_growth) else None),
        ("盈利修正：处于第二阶段（共识预期从下调转上调）",
         (upside and upside > 0.15) if upside else None),
        ("质量过滤：ROIC>资本成本、FCF持续为正",
         (roe and roe > 0.12) if roe else None),
        ("存在可识别催化剂（管理层变更/并购/新产品/周期拐点）",
         None),  # 需人工确认
        ("竞争地位稳固（市场份额稳定或扩大）",
         (revenue_growth and revenue_growth > 0) if revenue_growth else None),
        ("仓位和风控已设定（明确止损位和加仓计划）",
         True if tech_data.get("atr14") else None),
        ("市场环境评估（Druckenmiller三信号未同时触发）",
         None),  # 需人工确认
        ("行为偏差检查（非FOMO，排除锚定效应）",
         None),  # 需人工确认
        ("聪明钱信号对齐（内部人买入而非大规模减持）",
         None),  # 需人工确认
        ("市场/行业框架匹配（使用正确估值方法）",
         True),
    ]

    for i, (item, ok) in enumerate(checks_buy, 1):
        mark = signal(ok)
        if ok is True:
            score_buy += 1
        elif ok is False:
            score_sell += 1
        print(f"  {i:2d}. {mark} {item}")

    print("\n🚨 卖出Checklist（顶级机构10条标准）")
    checks_sell = [
        ("投资逻辑是否已改变（基本面论据被否定）",
         (upside and upside < 0) if upside else None),
        ("逆向DCF：隐含增长率已超结构性天花板",
         (implied_growth and hist_growth and (implied_growth - hist_growth) > 0.05) if (implied_growth and hist_growth) else None),
        ("盈利修正进入第四阶段（预期从上调转下调）",
         (upside and upside < 0.05) if upside else None),
        ("利润率持续压缩",
         None),  # 需人工确认季度数据
        ("竞争护城河在恶化（市场份额流失）",
         (revenue_growth and revenue_growth < -0.05) if revenue_growth else None),
        ("存在更好的资本配置机会（机会成本考量）",
         None),  # 需人工确认
        ("止损位被击穿 / 时间止损触发",
         (price and sma200 and price < sma200 * 0.95) if (price and sma200) else None),
        ("内部人大规模减持（机会主义卖出）",
         None),  # 需人工确认
        ("情绪偏差：是否因损失厌恶'等回本'？",
         None),  # 需人工确认
        ("市场周期位置：熊市中公允价值是天花板",
         None),  # 需人工确认
    ]

    sell_triggers = 0
    for i, (item, ok) in enumerate(checks_sell, 1):
        mark = signal(ok)
        if ok is True:
            sell_triggers += 1
        print(f"  {i:2d}. {mark} {item}")

    # --- 最终建议 ---
    print("\n" + "="*50)
    print("【最终建议】")
    print("="*50)

    # 技术信号综合
    tech_positive = sum([
        momentum and momentum > 0,
        rsi and 30 < rsi < 70,
        "金叉" in macd_cross or "多头" in macd_cross,
        price and sma50 and price > sma50,
    ])

    # 基本面综合
    fundamental_positive = sum([
        upside and upside > 0.10,
        peg and peg < 1.2,
        roe and roe > 0.12,
        revenue_growth and revenue_growth > 0,
    ])

    total_positive = tech_positive + fundamental_positive
    total_checked = 8  # 有效检查项

    if sell_triggers >= 2:
        verdict = "🔴 建议卖出"
        reason = "多项卖出信号触发，投资逻辑可能已改变"
    elif total_positive >= 5:
        verdict = "🟢 建议买入"
        reason = "基本面和技术面共振向上，风险收益比良好"
    elif total_positive >= 3:
        verdict = "🟡 建议持有/观望"
        reason = "信号混合，等待更明确的催化剂或技术确认"
    else:
        verdict = "🔴 建议回避"
        reason = "正面信号不足，等待更好的买入时机"

    print(f"\n  {verdict}")
    print(f"  理由：{reason}")
    print(f"  信号评分：{total_positive}/{total_checked}项正面")
    print(f"\n  ⚠️ 关键风险提示：")
    print(f"  • 本分析基于公开数据，无法获取内部人交易、暗池信号、期权偏斜等完整信息")
    print(f"  • 标注'需人工确认'的项目必须结合实际判断，尤其是催化剂识别和聪明钱信号")
    print(f"  • 任何买卖决策前请确认止损位已设定，控制单笔风险不超过账户的1-2%")
    print(f"  • Howard Marks：「投资成功不在于'买好东西'，而在于'买得好'。」")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="股票买卖点分析（顶级机构决策框架）")
    parser.add_argument("--market", required=True, choices=["US", "CN", "HK"], help="市场：US/CN/HK")
    parser.add_argument("--ticker", required=True, help="股票代码（如：AAPL, 600519.SS, 0700.HK）")
    args = parser.parse_args()

    market_names = {"US": "美股", "CN": "A股", "HK": "港股"}
    print("\n" + "="*50)
    print(f"📊 股票分析报告 | {args.ticker} ({market_names[args.market]})")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"框架来源：《二级市场买卖点判断：顶级机构的系统性决策框架》")
    print("="*50)

    try:
        ticker_obj, hist, info = fetch_data(args.ticker)
    except Exception as e:
        print(f"❌ 数据获取失败：{e}")
        sys.exit(1)

    if hist.empty:
        print("❌ 未获取到历史行情数据，请检查股票代码是否正确")
        sys.exit(1)

    # 六大维度分析
    fund_data = analyze_fundamental(info, hist)
    tech_data = analyze_technical(hist)
    market_data = analyze_market_structure(args.market, info, tech_data)
    analyze_risk_management(tech_data, fund_data)
    analyze_behavioral(hist, info)
    final_decision(args.market, fund_data, tech_data, market_data)

    print("\n" + "="*50)
    print("分析完毕。记住：框架是工具，纪律是引擎，自我认知才是燃料。")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
