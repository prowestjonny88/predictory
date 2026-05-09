import re
import json

en_keys = {
    "explain.key.metric": "Metric",
    "explain.key.amount": "Amount",
    "explain.key.scope": "Scope",
    "explain.key.source": "Source",
    "explain.key.pendingActions": "Actions awaiting review",
    "explain.key.ingredientShortages": "Ingredient shortages",
    "explain.key.forecastRun": "Forecast run",
    "explain.key.outletId": "Outlet ID",
    "explain.key.outlet": "Outlet",
    "explain.key.skuId": "SKU ID",
    "explain.key.sku": "SKU",
    "explain.key.skuCategory": "SKU category",
    "explain.key.daypart": "Daypart",
    "explain.key.lowDemand": "Low-demand scenario",
    "explain.key.expectedDemand": "Expected-demand scenario",
    "explain.key.highDemand": "High-demand scenario",
    "explain.key.recommendedPrep": "Recommended prep",
    "explain.key.finalPrep": "Final prep",
    "explain.key.currentStock": "Current stock",
    "explain.key.openingStock": "Opening stock",
    "explain.key.batchSize": "Batch size",
    "explain.key.wasteCost": "Waste cost",
    "explain.key.stockoutCost": "Stockout cost",
    "explain.key.stockoutExposure": "Stockout exposure",
    "explain.key.wasteExposure": "Waste exposure",
    "explain.key.priorityScore": "Priority score",
    "explain.key.priorityReason": "Priority reason",
    "explain.key.needQuantity": "Need quantity",
    "explain.key.reorderQuantity": "Reorder quantity",
    "explain.key.urgency": "Urgency",
    "explain.key.drivingSkus": "Driving SKUs",
    "explain.value.backendReplenishmentPlan": "Backend replenishment plan",
    "explain.value.backendReplenishmentBreakdown": "Backend replenishment breakdown",
    "explain.value.backendWasteAlert": "Backend waste alert",
    "explain.value.backendStockoutAlert": "Backend stockout alert",
}

ms_keys = {
    "explain.key.metric": "Metrik",
    "explain.key.amount": "Jumlah",
    "explain.key.scope": "Skop",
    "explain.key.source": "Sumber",
    "explain.key.pendingActions": "Tindakan menunggu semakan",
    "explain.key.ingredientShortages": "Kekurangan bahan",
    "explain.key.forecastRun": "Larian ramalan",
    "explain.key.outletId": "ID Cawangan",
    "explain.key.outlet": "Cawangan",
    "explain.key.skuId": "ID SKU",
    "explain.key.sku": "SKU",
    "explain.key.skuCategory": "Kategori SKU",
    "explain.key.daypart": "Waktu",
    "explain.key.lowDemand": "Senario permintaan rendah",
    "explain.key.expectedDemand": "Senario permintaan dijangka",
    "explain.key.highDemand": "Senario permintaan tinggi",
    "explain.key.recommendedPrep": "Persediaan disyorkan",
    "explain.key.finalPrep": "Persediaan akhir",
    "explain.key.currentStock": "Stok semasa",
    "explain.key.openingStock": "Stok pembukaan",
    "explain.key.batchSize": "Saiz kelompok",
    "explain.key.wasteCost": "Kos pembaziran",
    "explain.key.stockoutCost": "Kos kehabisan stok",
    "explain.key.stockoutExposure": "Pendedahan kehabisan stok",
    "explain.key.wasteExposure": "Pendedahan pembaziran",
    "explain.key.priorityScore": "Skor keutamaan",
    "explain.key.priorityReason": "Sebab keutamaan",
    "explain.key.needQuantity": "Kuantiti diperlukan",
    "explain.key.reorderQuantity": "Kuantiti pesanan semula",
    "explain.key.urgency": "Kecemasan",
    "explain.key.drivingSkus": "SKU Pemacu",
    "explain.value.backendReplenishmentPlan": "Pelan pengisian semula belakang",
    "explain.value.backendReplenishmentBreakdown": "Pecahan pengisian semula belakang",
    "explain.value.backendWasteAlert": "Amaran pembaziran belakang",
    "explain.value.backendStockoutAlert": "Amaran kehabisan stok belakang",
}

zh_keys = {
    "explain.key.metric": "指标",
    "explain.key.amount": "金额",
    "explain.key.scope": "范围",
    "explain.key.source": "来源",
    "explain.key.pendingActions": "待审核行动",
    "explain.key.ingredientShortages": "原料短缺",
    "explain.key.forecastRun": "预测运行",
    "explain.key.outletId": "门店 ID",
    "explain.key.outlet": "门店",
    "explain.key.skuId": "SKU ID",
    "explain.key.sku": "SKU",
    "explain.key.skuCategory": "SKU 类别",
    "explain.key.daypart": "时段",
    "explain.key.lowDemand": "低需求情景",
    "explain.key.expectedDemand": "预期需求情景",
    "explain.key.highDemand": "高需求情景",
    "explain.key.recommendedPrep": "推荐备货",
    "explain.key.finalPrep": "最终备货",
    "explain.key.currentStock": "当前库存",
    "explain.key.openingStock": "期初库存",
    "explain.key.batchSize": "批次大小",
    "explain.key.wasteCost": "浪费成本",
    "explain.key.stockoutCost": "缺货成本",
    "explain.key.stockoutExposure": "缺货风险敞口",
    "explain.key.wasteExposure": "浪费风险敞口",
    "explain.key.priorityScore": "优先级分数",
    "explain.key.priorityReason": "优先级原因",
    "explain.key.needQuantity": "需求数量",
    "explain.key.reorderQuantity": "补货数量",
    "explain.key.urgency": "紧急程度",
    "explain.key.drivingSkus": "驱动 SKU",
    "explain.value.backendReplenishmentPlan": "后端补货计划",
    "explain.value.backendReplenishmentBreakdown": "后端补货明细",
    "explain.value.backendWasteAlert": "后端浪费预警",
    "explain.value.backendStockoutAlert": "后端缺货预警",
}

def inject_keys(filepath, dict_keys):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = []
    for k, v in dict_keys.items():
        # Check if already present to avoid duplicates
        if f'"{k}":' not in content:
            lines.append(f'  "{k}": "{v}",')
            
    if not lines:
        print(f"No new keys to add for {filepath}")
        return

    # Find where explain keys are to insert alphabetically
    insert_pos = content.find('"explain.loadingWriting":')
    if insert_pos == -1:
        # fallback, just put before last brace
        insert_pos = content.rfind('}')
        
    # We'll just insert before the match
    new_content = content[:insert_pos] + "\n".join(lines) + "\n" + content[insert_pos:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Added {len(lines)} keys to {filepath}")

inject_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\en.ts', en_keys)
inject_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\ms.ts', ms_keys)
inject_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\zh-CN.ts', zh_keys)

