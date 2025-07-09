
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pandas as pd
import requests
from io import BytesIO
from youtubedata import main as search_main_function

# 영어 → 한글 매핑
COLUMN_TRANSLATION = {
    "title": "제목",
    "channel_title": "채널명",
    "published_at": "업로드 날짜",
    "duration": "영상 길이",
    "subscriber_count_simple": "구독자 수",
    "view_simple": "조회수 한글표현",
    "view_count_formatted": "조회수",
    "reaction_score": "반응도 (조회수/구독자)",
    "reaction_level": "반응 해석",
    "url": "영상 링크"
}

class YouTubeSearchApp:
    def __init__(self, root):
        self.root = root
        root.title("유튜브 반응도 검색기")
        root.geometry("1300x600")

        # 검색창
        self.top_frame = tk.Frame(root)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        tk.Label(self.top_frame, text="검색어:").grid(row=0, column=0)
        self.query_entry = tk.Entry(self.top_frame, width=40)
        self.query_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.top_frame, text="검색 개수:").grid(row=0, column=2)
        self.count_entry = tk.Entry(self.top_frame, width=10)
        self.count_entry.grid(row=0, column=3)
        self.count_entry.insert(0, "30")

        tk.Button(self.top_frame, text="검색", command=self.run_search).grid(row=0, column=4, padx=10)

        # 테이블
        self.table_frame = tk.Frame(root)
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=3)

        self.tree_scroll_y = tk.Scrollbar(self.table_frame)
        self.tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self.table_frame, yscrollcommand=self.tree_scroll_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)

        # 썸네일
        self.thumb_frame = tk.Frame(root)
        self.thumb_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        root.grid_columnconfigure(1, weight=1)

        self.thumb_label = tk.Label(self.thumb_frame, text="썸네일 미리보기")
        self.thumb_label.pack()

        self.thumbnail_img = None
        self.df = pd.DataFrame()
        self.eng_columns = []

    def run_search(self):
        query = self.query_entry.get().strip()
        try:
            max_results = int(self.count_entry.get().strip())
        except ValueError:
            max_results = 30

        df, raw_data = search_main_function(query, max_results, return_df=True)
        self.df_raw = raw_data

        # 썸네일 관련 URL 컬럼 제외
        drop_cols = ["thumbnail.url", "thumbnail_url"]
        for col in drop_cols:
            if col in df.columns:
                df = df.drop(columns=col)

        self.df = df
        self.eng_columns = list(self.df.columns)

        # 한글 컬럼명 변환
        display_columns = [COLUMN_TRANSLATION.get(col, col) for col in self.eng_columns]

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = display_columns
        self.tree["show"] = "headings"

        for col in display_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)

        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=list(row))



    def on_tree_select(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return

        index = self.tree.index(item_id)
        if index >= len(self.df_raw):
            return

        try:
            video_id = self.df_raw[index].get("video_id", "")
            print("video_id:", video_id)
            if not video_id:
                raise ValueError("video_id 없음")
        except Exception as e:
            self.thumb_label.config(text=f"[오류] video_id 추출 실패: {e}", image="")
            return

        # 썸네일 표시
        url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img_data = Image.open(BytesIO(response.content))
            img_data = img_data.resize((320, 180))
            self.thumbnail_img = ImageTk.PhotoImage(img_data)
            self.thumb_label.configure(image=self.thumbnail_img, text="")
            self.thumb_label.image = self.thumbnail_img
        except Exception as e:
            self.thumb_label.config(text=f"[썸네일 로딩 실패] {e}", image="")




if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeSearchApp(root)
    root.mainloop()
