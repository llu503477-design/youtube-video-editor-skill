# Layout Agent Prompt

輸入：

- canvas
- safe zones
- blocked zones
- text
- template
- font metrics

輸出只包含位置、縮放與斷行決策。

優先順序：

1. 不遮人臉、產品、操作區。
2. 不進入平台安全區。
3. 最多兩行。
4. 優先重新斷句，再縮字。
5. 字號不得低於 preset 最小值。
6. 無法安全放置時，使用半透明背景或上方位置。
7. 不改寫語意。
