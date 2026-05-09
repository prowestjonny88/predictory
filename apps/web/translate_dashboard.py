import json

ms_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\ms.ts'
zh_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\zh-CN.ts'

with open(ms_path, 'r', encoding='utf-8') as f:
    ms_content = f.read()

translations_ms = {
    '"dashboard.allCleared": "All Cleared"': '"dashboard.allCleared": "Semua Selesai"',
    '"dashboard.approval": "Approval"': '"dashboard.approval": "Kelulusan"',
    '"dashboard.brief.exposureCurrency": "Full-plan exposure: {{amount}}."': '"dashboard.brief.exposureCurrency": "Pendedahan pelan penuh: {{amount}}."',
    '"dashboard.brief.nextStep": "Next step: review the {{count}} priority decisions before bulk approval."': '"dashboard.brief.nextStep": "Langkah seterusnya: semak {{count}} keputusan keutamaan sebelum kelulusan pukal."',
    '"dashboard.brief.stockoutDominant": "Stockout risk is the dominant exposure."': '"dashboard.brief.stockoutDominant": "Risiko kehabisan stok adalah pendedahan utama."',
    '"dashboard.brief.topDecision": "Top decision: prepare {{units}} units of {{sku}} for {{outlet}} {{daypart}}."': '"dashboard.brief.topDecision": "Keputusan utama: sediakan {{units}} unit {{sku}} untuk {{outlet}} {{daypart}}."',
    '"dashboard.brief.totalLines": "{{count}} total plan lines remain in the backend plan."': '"dashboard.brief.totalLines": "{{count}} jumlah garis pelan kekal dalam pelan belakang."',
    '"dashboard.brief.wasteDominant": "Waste risk is the dominant exposure."': '"dashboard.brief.wasteDominant": "Risiko pembaziran adalah pendedahan utama."',
    '"dashboard.briefSource": "Operations brief"': '"dashboard.briefSource": "Ringkasan operasi"',
    '"dashboard.explainStockout": "Explain"': '"dashboard.explainStockout": "Terangkan"',
    '"dashboard.explainStockoutTitle": "Stockout exposure"': '"dashboard.explainStockoutTitle": "Pendedahan kehabisan stok"',
    '"dashboard.explainWaste": "Explain"': '"dashboard.explainWaste": "Terangkan"',
    '"dashboard.explainWasteTitle": "Waste exposure"': '"dashboard.explainWasteTitle": "Pendedahan pembaziran"',
    '"dashboard.exposureSubtitle": "Backend full-plan stockout and waste exposure combined."': '"dashboard.exposureSubtitle": "Gabungan pendedahan kehabisan stok dan pembaziran pelan penuh belakang."',
    '"dashboard.forecastRun": "Forecast run"': '"dashboard.forecastRun": "Larian ramalan"',
    '"dashboard.fullPlanExposure": "Full-plan exposure"': '"dashboard.fullPlanExposure": "Pendedahan pelan penuh"',
    '"dashboard.fullPlanStockoutExposure": "Full-plan stockout exposure"': '"dashboard.fullPlanStockoutExposure": "Pendedahan kehabisan stok pelan penuh"',
    '"dashboard.fullPlanWasteExposure": "Full-plan waste exposure"': '"dashboard.fullPlanWasteExposure": "Pendedahan pembaziran pelan penuh"',
    '"dashboard.noDailyPlan": "No backend daily plan is available for this date."': '"dashboard.noDailyPlan": "Tiada pelan harian belakang tersedia untuk tarikh ini."',
    '"dashboard.noExceptions": "No exceptions for this plan date."': '"dashboard.noExceptions": "Tiada pengecualian untuk tarikh pelan ini."',
    '"dashboard.noShortage": "No shortage"': '"dashboard.noShortage": "Tiada kekurangan"',
    '"dashboard.openRiskCenter": "Open Risk Center"': '"dashboard.openRiskCenter": "Buka Pusat Risiko"',
    '"dashboard.pendingReview": "Pending review"': '"dashboard.pendingReview": "Menunggu semakan"',
    '"dashboard.priorityDecisions": "Priority Decisions"': '"dashboard.priorityDecisions": "Keputusan Keutamaan"',
    '"dashboard.priorityPlan": "Priority plan"': '"dashboard.priorityPlan": "Pelan keutamaan"',
    '"dashboard.priorityRatio": "{{priority}} priority / {{total}} total"': '"dashboard.priorityRatio": "{{priority}} keutamaan / {{total}} jumlah"',
    '"dashboard.prioritySubtitle": "Managers review priority decisions first and bulk-approve low-risk lines."': '"dashboard.prioritySubtitle": "Pengurus menyemak keputusan keutamaan dahulu dan meluluskan garis berisiko rendah secara pukal."',
    '"dashboard.readiness": "Tomorrow readiness"': '"dashboard.readiness": "Kesediaan esok"',
    '"dashboard.replenishment": "Replenishment"': '"dashboard.replenishment": "Pengisian Semula"',
    '"dashboard.reviewDailyPlan": "Review Tomorrow"': '"dashboard.reviewDailyPlan": "Semak Esok"',
    '"dashboard.reviewDecision": "Review decision"': '"dashboard.reviewDecision": "Semak keputusan"',
    '"dashboard.reviewProgress": "{{reviewed}} of {{total}} priority decisions reviewed"': '"dashboard.reviewProgress": "{{reviewed}} daripada {{total}} keputusan keutamaan telah disemak"',
    '"dashboard.shortages": "{{count}} shortages"': '"dashboard.shortages": "{{count}} kekurangan"',
    '"dashboard.stockoutSubtitle": "Potential lost margin from under-prep across the backend plan."': '"dashboard.stockoutSubtitle": "Potensi margin hilang akibat kurang persediaan di seluruh pelan belakang."',
    '"dashboard.tomorrowBrief": "Tomorrow Brief"': '"dashboard.tomorrowBrief": "Ringkasan Esok"',
    '"dashboard.topDecisions": "Top decisions to review"': '"dashboard.topDecisions": "Keputusan utama untuk disemak"',
    '"dashboard.totalPlanLines": "{{count}} total plan lines"': '"dashboard.totalPlanLines": "{{count}} jumlah garis pelan"',
    '"dashboard.wasteSubtitle": "Potential spoilage exposure from over-prep across the backend plan."': '"dashboard.wasteSubtitle": "Potensi pendedahan kerosakan akibat terlebih persediaan di seluruh pelan belakang."',
}

for k, v in translations_ms.items():
    ms_content = ms_content.replace(k, v)

with open(ms_path, 'w', encoding='utf-8') as f:
    f.write(ms_content)

with open(zh_path, 'r', encoding='utf-8') as f:
    zh_content = f.read()

translations_zh = {
    '"dashboard.allCleared": "All Cleared"': '"dashboard.allCleared": "全部清除"',
    '"dashboard.approval": "Approval"': '"dashboard.approval": "审批"',
    '"dashboard.brief.exposureCurrency": "Full-plan exposure: {{amount}}."': '"dashboard.brief.exposureCurrency": "全计划风险敞口：{{amount}}。"',
    '"dashboard.brief.nextStep": "Next step: review the {{count}} priority decisions before bulk approval."': '"dashboard.brief.nextStep": "下一步：在批量审批前审核 {{count}} 个优先决策。"',
    '"dashboard.brief.stockoutDominant": "Stockout risk is the dominant exposure."': '"dashboard.brief.stockoutDominant": "缺货风险为主要风险。"',
    '"dashboard.brief.topDecision": "Top decision: prepare {{units}} units of {{sku}} for {{outlet}} {{daypart}}."': '"dashboard.brief.topDecision": "首要决策：在 {{daypart}} 为 {{outlet}} 准备 {{units}} 个 {{sku}}。"',
    '"dashboard.brief.totalLines": "{{count}} total plan lines remain in the backend plan."': '"dashboard.brief.totalLines": "后端计划中还有 {{count}} 行总计划。"',
    '"dashboard.brief.wasteDominant": "Waste risk is the dominant exposure."': '"dashboard.brief.wasteDominant": "浪费风险为主要风险。"',
    '"dashboard.briefSource": "Operations brief"': '"dashboard.briefSource": "运营简报"',
    '"dashboard.explainStockout": "Explain"': '"dashboard.explainStockout": "说明"',
    '"dashboard.explainStockoutTitle": "Stockout exposure"': '"dashboard.explainStockoutTitle": "缺货风险敞口"',
    '"dashboard.explainWaste": "Explain"': '"dashboard.explainWaste": "说明"',
    '"dashboard.explainWasteTitle": "Waste exposure"': '"dashboard.explainWasteTitle": "浪费风险敞口"',
    '"dashboard.exposureSubtitle": "Backend full-plan stockout and waste exposure combined."': '"dashboard.exposureSubtitle": "后端全计划缺货和浪费综合风险。"',
    '"dashboard.forecastRun": "Forecast run"': '"dashboard.forecastRun": "预测运行"',
    '"dashboard.fullPlanExposure": "Full-plan exposure"': '"dashboard.fullPlanExposure": "全计划风险敞口"',
    '"dashboard.fullPlanStockoutExposure": "Full-plan stockout exposure"': '"dashboard.fullPlanStockoutExposure": "全计划缺货敞口"',
    '"dashboard.fullPlanWasteExposure": "Full-plan waste exposure"': '"dashboard.fullPlanWasteExposure": "全计划浪费敞口"',
    '"dashboard.noDailyPlan": "No backend daily plan is available for this date."': '"dashboard.noDailyPlan": "该日期没有后端每日计划。"',
    '"dashboard.noExceptions": "No exceptions for this plan date."': '"dashboard.noExceptions": "此计划日期无异常。"',
    '"dashboard.noShortage": "No shortage"': '"dashboard.noShortage": "无短缺"',
    '"dashboard.openRiskCenter": "Open Risk Center"': '"dashboard.openRiskCenter": "打开风险中心"',
    '"dashboard.pendingReview": "Pending review"': '"dashboard.pendingReview": "待审核"',
    '"dashboard.priorityDecisions": "Priority Decisions"': '"dashboard.priorityDecisions": "优先决策"',
    '"dashboard.priorityPlan": "Priority plan"': '"dashboard.priorityPlan": "优先计划"',
    '"dashboard.priorityRatio": "{{priority}} priority / {{total}} total"': '"dashboard.priorityRatio": "{{priority}} 优先 / 共 {{total}}"',
    '"dashboard.prioritySubtitle": "Managers review priority decisions first and bulk-approve low-risk lines."': '"dashboard.prioritySubtitle": "经理首先审核优先决策，并批量批准低风险项目。"',
    '"dashboard.readiness": "Tomorrow readiness"': '"dashboard.readiness": "明日就绪情况"',
    '"dashboard.replenishment": "Replenishment"': '"dashboard.replenishment": "补货"',
    '"dashboard.reviewDailyPlan": "Review Tomorrow"': '"dashboard.reviewDailyPlan": "审核明日计划"',
    '"dashboard.reviewDecision": "Review decision"': '"dashboard.reviewDecision": "审核决策"',
    '"dashboard.reviewProgress": "{{reviewed}} of {{total}} priority decisions reviewed"': '"dashboard.reviewProgress": "已审核 {{total}} 个优先决策中的 {{reviewed}} 个"',
    '"dashboard.shortages": "{{count}} shortages"': '"dashboard.shortages": "{{count}} 个短缺"',
    '"dashboard.stockoutSubtitle": "Potential lost margin from under-prep across the backend plan."': '"dashboard.stockoutSubtitle": "整个后端计划中由于备货不足造成的潜在利润损失。"',
    '"dashboard.tomorrowBrief": "Tomorrow Brief"': '"dashboard.tomorrowBrief": "明日简报"',
    '"dashboard.topDecisions": "Top decisions to review"': '"dashboard.topDecisions": "主要审核决策"',
    '"dashboard.totalPlanLines": "{{count}} total plan lines"': '"dashboard.totalPlanLines": "共 {{count}} 行计划"',
    '"dashboard.wasteSubtitle": "Potential spoilage exposure from over-prep across the backend plan."': '"dashboard.wasteSubtitle": "整个后端计划中因超量备货造成的潜在损坏风险。"',
}

for k, v in translations_zh.items():
    zh_content = zh_content.replace(k, v)

with open(zh_path, 'w', encoding='utf-8') as f:
    f.write(zh_content)

print("Translations applied successfully.")
