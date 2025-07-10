
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pandas as pd
import requests
from io import BytesIO
from youtubedata import main as search_main_function
import json
import os
from tkinter import messagebox

CONFIG_FILE = "config.json"

def load_api_key():
    if os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("api_key", "")
    return ""

def save_api_key_to_file(api_key):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key}, f, ensure_ascii=False, indent=2)


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
def copy_selected_cell(self, event):
    try:
        selected = self.tree.selection()[0]
        values = self.tree.item(selected)["values"]
        col = self.tree.identify_column(event.x)
        col_index = int(col.replace('#', '')) - 1
        copied_value = str(values[col_index])
        self.root.clipboard_clear()
        self.root.clipboard_append(copied_value)
        self.root.update()
    except Exception as e:
        print("[복사 실패]", e)
        
class YouTubeSearchApp:
    def __init__(self, root):
        self.root = root
        root.title("유튜브 반응도 검색기")
        root.geometry("1300x600")
        root.resizable(True, True)

        # 전체 영역 확장되도록 설정
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=3)   # 테이블 쪽 비중
        root.grid_columnconfigure(1, weight=2)   # 썸네일 쪽 비중
        # 검색창
        self.top_frame = tk.Frame(root)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        # ✅ API 키 입력
        tk.Label(self.top_frame, text="API 키:").grid(row=0, column=0)
        self.api_entry = tk.Entry(self.top_frame, width=50)
        self.api_entry.grid(row=0, column=1, padx=5)
        self.api_entry.insert(0, load_api_key())
        tk.Button(self.top_frame, text="저장", command=self.save_api_key).grid(row=0, column=2)

        # ✅ 검색어 입력
        tk.Label(self.top_frame, text="검색어:").grid(row=1, column=0)
        self.query_entry = tk.Entry(self.top_frame, width=40)
        self.query_entry.grid(row=1, column=1, padx=5)

        tk.Label(self.top_frame, text="검색 개수:").grid(row=1, column=2)
        self.count_entry = tk.Entry(self.top_frame, width=10)
        self.count_entry.grid(row=1, column=3)
        self.count_entry.insert(0, "30")

        tk.Button(self.top_frame, text="검색", command=self.run_search).grid(row=1, column=4, padx=10)

        # # 테이블
        # self.table_frame = tk.Frame(root)
        # self.table_frame.grid(row=1, column=0, sticky="nsew")
        # root.grid_rowconfigure(1, weight=1)
        # root.grid_columnconfigure(0, weight=3)

        # self.tree_scroll_y = tk.Scrollbar(self.table_frame)
        # self.tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # self.tree = ttk.Treeview(self.table_frame, yscrollcommand=self.tree_scroll_y.set)
        # self.tree.pack(fill=tk.BOTH, expand=True)
        # self.tree_scroll_y.config(command=self.tree.yview)
        # self.tree.bind("<ButtonRelease-1>", self.on_tree_select)
        # self.tree.bind("<Control-c>", self.copy_selected_cell)

        # # 썸네일
        # self.thumb_frame = tk.Frame(root, width=650, height=350)  # ✅ 가로 공간 확보
        # self.thumb_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        # root.grid_columnconfigure(1, weight=1)
        
        # self.thumb_frame.bind("<Configure>", self.on_thumb_resize)
        
        # self.thumb_label = tk.Label(self.thumb_frame, text="썸네일 미리보기", anchor="center")
        # self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")  # 중앙 정렬
        # self.thumb_label.pack(fill=tk.BOTH, expand=True)  
        # root.geometry("1400x700")  # ✅ 넓이 늘림
        # self.thumbnail_img = None
        # self.df = pd.DataFrame()
        # self.eng_columns = []
         # ✅ PanedWindow 생성 (수평 분할)
        self.paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.paned.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # ✅ 테이블 프레임
        self.table_frame = tk.Frame(self.paned)
        self.tree_scroll_y = tk.Scrollbar(self.table_frame)
        self.tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self.table_frame, yscrollcommand=self.tree_scroll_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)
        self.tree.bind("<Control-c>", self.copy_selected_cell)

        self.paned.add(self.table_frame, minsize=400)  # 왼쪽 영역 추가

        # ✅ 썸네일 프레임
        self.thumb_frame = tk.Frame(self.paned)
        self.thumb_frame.bind("<Configure>", self.on_thumb_resize)

        self.thumb_label = tk.Label(self.thumb_frame, text="썸네일 미리보기", anchor="center")
        self.thumb_label.pack(fill=tk.BOTH, expand=True)

        self.paned.add(self.thumb_frame, minsize=300)  # 오른쪽 영역 추가
                # ✅ 초기 분할 위치 설정 (8:2 비율)
        self.root.update_idletasks()  # geometry가 잡힌 이후에 sash 위치 조정
        self.root.after(100, lambda: self.paned.sash_place(0, int(self.root.winfo_width() * 0.8), 0))

    def save_api_key(self):
        api_key = self.api_entry.get().strip()
        save_api_key_to_file(api_key)
        tk.messagebox.showinfo("저장 완료", "API 키가 저장되었습니다.")

    def run_search(self):
        query = self.query_entry.get().strip()
        api_key = self.api_entry.get().strip() 
        try:
            max_results = int(self.count_entry.get().strip())
        except ValueError:
            max_results = 30
        if not api_key:
            self.thumb_label.config(text="❗ API 키를 입력하세요", image="")
            return
        
        df, raw_data = search_main_function(query, max_results, api_key=api_key, return_df=True)
        self.df_raw = raw_data

        # 썸네일 관련 URL 컬럼 제외
        drop_cols = ["thumbnail.url", "thumbnail_url"]
        for col in drop_cols:
            if col in df.columns:
                df = df.drop(columns=col)

        self.df = df
        self.eng_columns = list(self.df.columns)

        # 📌 video_id를 TreeView에서 제외한 버전
        df_display = self.df.drop(columns=["video_id"])
        # 한글 컬럼명 변환
        display_columns = [COLUMN_TRANSLATION.get(col, col) for col in df_display.columns]

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = display_columns
        self.tree["show"] = "headings"

        for col in display_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)

        for _, row in df_display.iterrows():
            self.tree.insert("", "end", values=list(row))

    def on_thumb_resize(self, event):
        if hasattr(self, "current_video_id") and self.current_video_id:
            self.update_thumbnail(self.current_video_id)
            
    def copy_selected_cell(self, event):
        try:
            selected = self.tree.selection()[0]
            values = self.tree.item(selected)["values"]
            col = self.tree.identify_column(event.x)
            col_index = int(col.replace('#', '')) - 1
            copied_value = str(values[col_index])
            self.root.clipboard_clear()
            self.root.clipboard_append(copied_value)
            self.root.update()
        except Exception as e:
            print("[복사 실패]", e)

    def update_thumbnail(self, video_id):
        url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img_data = Image.open(BytesIO(response.content))

            # 현재 프레임 크기 측정
            frame_width = self.thumb_frame.winfo_width()
            frame_height = self.thumb_frame.winfo_height()

            if frame_width <= 1 or frame_height <= 1:
                frame_width, frame_height = 600, 338  # 초기값

            # 비율 유지하며 프레임 내에 맞추기
            img_data.thumbnail((frame_width, frame_height), Image.LANCZOS)

            self.thumbnail_img = ImageTk.PhotoImage(img_data)
            self.thumb_label.configure(image=self.thumbnail_img, text="")
            self.thumb_label.image = self.thumbnail_img

        except Exception as e:
            self.thumb_label.config(text=f"[썸네일 로딩 실패] {e}", image="")
    # def on_tree_select(self, event):
        
    #     item_id = self.tree.focus()
    #     if not item_id:
    #         return

    #     index = self.tree.index(item_id)
    #     if index >= len(self.df_raw):
    #         return

    #     try:
    #         video_id = self.df_raw[index].get("video_id", "")
    #         # video_id = self.df.iloc[index]["video_id"]
    #         print("video_id:", video_id)
    #         if not video_id:
    #             raise ValueError("video_id 없음")
    #     except Exception as e:
    #         self.thumb_label.config(text=f"[오류] video_id 추출 실패: {e}", image="")
    #         return

    #     # 썸네일 표시
    #     # 썸네일 표시
    #     url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    #     try:
    #         response = requests.get(url, timeout=5)
    #         response.raise_for_status()
    #         img_data = Image.open(BytesIO(response.content))
            
    #         # ✅ 비율 유지하며 썸네일 크기 조정
    #         img_data.thumbnail((600, 338), Image.LANCZOS)
    #         self.thumbnail_img = ImageTk.PhotoImage(img_data)
    #         self.thumb_label.configure(image=self.thumbnail_img, text="", width=600, height=338)


    #         self.thumbnail_img = ImageTk.PhotoImage(img_data)
    #         self.thumb_label.configure(image=self.thumbnail_img, text="")
    #         self.thumb_label.image = self.thumbnail_img
    #     except Exception as e:
    #         self.thumb_label.config(text=f"[썸네일 로딩 실패] {e}", image="")

    def on_tree_select(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return

        index = self.tree.index(item_id)
        if index >= len(self.df_raw):
            return

        try:
            video_id = self.df_raw[index].get("video_id", "")
            self.current_video_id = video_id  # 현재 영상 기억해두기
            if not video_id:
                raise ValueError("video_id 없음")
        except Exception as e:
            self.thumb_label.config(text=f"[오류] video_id 추출 실패: {e}", image="")
            return

        self.update_thumbnail(video_id)



if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeSearchApp(root)
    root.mainloop()
