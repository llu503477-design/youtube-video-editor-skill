# Visual Director Prompt

將語意事件映射到已註冊模板。

不可創造未知 templateId。

映射：

- normal_dialogue / important_fact -> clean-bottom
- question -> question-pop
- punchline / answer -> impact-slam
- warning -> warning-alert
- number -> big-number
- chapter_title -> chapter-title
- quotation -> quote-card
- call_to_action -> cta-card

效果預算：

- 同一 10 秒最多 1 個 strongEffect。
- 超過預算時，保留最高 intensity，其餘降級為 clean-bottom。
- 連續兩個 strongEffect 間隔建議大於 2 秒。
- 一般字幕只能淡入、淡出或單一關鍵字高亮。
