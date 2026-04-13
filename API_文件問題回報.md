# Moti-Physio API 文件問題回報

**回報日期：** 2026-04-13
**API 版本：** v1
**文件來源：** Public_MotiPhysio_API_Example（GitHub）+ API 規格文件

---

## 問題總覽

在實際串接過程中，發現 API 文件描述與實際回傳行為有多處不一致，導致開發端需額外偵錯與調整。以下逐一列出差異。

---

## 問題 1：Response 外層結構不一致

**影響端點：** `POST /v1/get_user_list`

| 項目 | 內容 |
|------|------|
| **文件描述** | 回傳 `{"users": [...]}`，資料包在 `users` key 中 |
| **實際行為** | 直接回傳陣列 `[{...}, {...}, ...]`，無外層包裝 |

**建議：** 更新文件範例，或統一 response 格式為 `{"users": [...]}` 以便前端解析。

---

## 問題 2：欄位命名風格不一致（snake_case vs camelCase）

**影響端點：** 所有端點

| 文件寫的（snake_case） | 實際回傳（camelCase） |
|------------------------|----------------------|
| `user_id` | `userId` |
| `register_date` | `signupDate` |
| `birth` | `birthDay`（且為 Unix timestamp，非 string） |
| `name` | `name`（一致） |
| `gender` | `gender`（一致，但文件寫 string，實際為 integer 0/1） |

**建議：** 統一文件中的欄位名稱與型別，與實際 API 回傳一致。

---

## 問題 3：文件中的欄位實際不存在

**影響端點：** `POST /v1/get_user_info`

| 項目 | 內容 |
|------|------|
| **文件描述** | Response 包含 `height`（身高 cm）和 `weight`（體重 kg） |
| **實際行為** | Response 中無 `height` 和 `weight` 欄位 |

**實際回傳欄位：** `programId`, `userId`, `phoneNum`, `name`, `age`, `gender`, `birthDay`, `signupDate`, `email`, `trainerId`, `contryCode`

**建議：** 更新文件，移除不存在的欄位，補上實際有但文件未提及的欄位（如 `programId`, `trainerId`, `contryCode`, `email`, `age`）。

---

## 問題 4：`gender` 欄位型別錯誤

**影響端點：** `get_user_list`, `get_user_info`

| 項目 | 內容 |
|------|------|
| **文件描述** | `gender` 型別為 `string` |
| **實際行為** | `gender` 型別為 `integer`（0 = 男, 1 = 女） |

**建議：** 更新文件型別為 integer，並說明對應值。

---

## 問題 5：`birth` / `birthDay` 型別錯誤

**影響端點：** `get_user_list`, `get_user_info`

| 項目 | 內容 |
|------|------|
| **文件描述** | `birth` 型別為 `string` |
| **實際行為** | `birthDay` 型別為 `integer`（Unix timestamp） |

**建議：** 更新欄位名稱與型別。

---

## 問題 6：分析列表 Response 結構不一致

**影響端點：** `get_user_static_analysis_list`, `get_user_ohs_analysis_list`, `get_user_ols_analysis_list`

| 項目 | 內容 |
|------|------|
| **文件描述** | 回傳 `{"analyses": [{"index": 0, "measurement_time": "...", "version": "..."}]}` |
| **實際行為** | 直接回傳陣列，欄位名為 `analysisIndex`、`measurementDate`（Unix timestamp），且包含完整的分析數據（14 項角度 + 14 項風險百分比） |

**實際回傳的額外欄位（文件未提及）：**
- `cameraAngle_x`, `cameraAngle_y`
- `acromialEnd_Angle`, `acromialEnd_RiskPercent`
- `C7CSL_Angle`, `C7CSL_RiskPercent`
- `pelvicAxialRotation_Angle`, `pelvicAxialRotation_RiskPercent`
- `Lt_HKA_Angle`, `Lt_HKA_RiskPercent`
- `Rt_HKA_Angle`, `Rt_HKA_RiskPercent`
- `cranialVertical_Angle`, `cranialVertical_RiskPercent`
- `roundShoulder_Angle`, `roundShoulder_RiskPercent`
- `thoracicKyphosis_Angle`, `thoracicKyphosis_RiskPercent`
- `lumbarLordosis_Angle`, `lumbarLordosis_RiskPercent`
- `pelvicShift_Angle`, `pelvicShift_RiskPercent`
- `pelvisTilt_Angle`, `pelvisTilt_RiskPercent`
- `kneeFlexionRecuvatum_Angle`, `kneeFlexionRecuvatum_RiskPercent`
- `scoliosisCobbs_Angle`, `scoliosisCobbs_RiskPercent`
- `pelvicObliquity_Angle`, `pelvicObliquity_RiskPercent`

**建議：** 補充完整的 response 欄位說明。這些數據對開發者非常有用，應在文件中清楚列出。

---

## 問題 7：`analysisIndex` 說明有誤（影響最大）

**影響端點：** `get_user_static_analysis_report`, `get_user_ohs_analysis_report`, `get_user_ols_analysis_report`

| 項目 | 內容 |
|------|------|
| **文件描述** | 「`index` 即為後續報告端點需要的 `analysis_index`（0-based）」，暗示為列表中的順序索引 |
| **實際行為** | `analysisIndex` 是 API 回傳的特定值（如 0, 1, 2, 3, 4, 5），非列表順序索引。且同一會員可能有多筆記錄共用相同 `analysisIndex`（例如 index=3 出現兩次） |

**造成的問題：** 開發者若按文件理解，用列表序號（0, 1, 2...）呼叫報告端點，會得到 `Invalid index` 錯誤或取得錯誤的報告。

**建議：** 明確說明報告端點的 `analysis_index` 參數必須使用分析列表回傳的 `analysisIndex` 值，而非列表中的位置索引。

---

## 問題 8：報告分類 Key 名稱不一致

**影響端點：** `get_user_static_analysis_report`

| 文件寫的 | 實際回傳 |
|----------|---------|
| `Skeleton` | `skeleton_result_sheet` |
| `Expert` | `expert_result_sheet` |
| `OriginalImage` | `original_image` |
| `OriginalImageResult` | `original_image_result_sheet` |
| `RiskRanking` | `risk_ranking_result_sheet` |

**建議：** 更新文件中的報告分類名稱，與實際 API 回傳一致。

---

## 問題 9：`contryCode` 疑似拼字錯誤

**影響端點：** `get_user_list`, `get_user_info`

| 項目 | 內容 |
|------|------|
| **實際欄位名** | `contryCode` |
| **正確拼寫** | `countryCode` |

**建議：** 確認是否為 typo，若是則修正 API 回傳欄位名。

---

## 總結

| 嚴重程度 | 問題數 | 說明 |
|----------|--------|------|
| **高** | 2 | 問題 7（analysisIndex 誤導）、問題 1（外層結構） — 直接導致串接失敗 |
| **中** | 4 | 問題 2, 3, 6, 8（欄位名/結構不符）— 需要額外偵錯才能正確解析 |
| **低** | 3 | 問題 4, 5, 9（型別/拼寫）— 不影響功能但影響開發體驗 |

建議優先修正**高嚴重度**的問題，這兩項會直接導致依照文件開發的程式無法正常運作。
