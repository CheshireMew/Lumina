# 提案: Settings Save Optimization (optimize-settings-save)

Introduce a bulk update endpoint for user/relationship data to significantly reduce latency when saving global settings impacting multiple characters.

## 为什么

Current settings save operation performs N+1 sequential HTTP requests (where N is character count), leading to noticeable UI freeze (2-3 seconds). Users require instant feedback.

## 目标

- Reduce "Save Settings" latency from O(N) to O(1).
- Eliminate "UI Freeze" caused by sequential waterfall requests.

## 非目标

- Full database transaction support (atomic file operations are sufficient for now).

## 变更内容

- **Backend**: Adds `POST /soul/user_name_bulk` endpoint in `routers/soul.py`.
- **Frontend**: Update `SettingsModal.tsx` to call new endpoint.
