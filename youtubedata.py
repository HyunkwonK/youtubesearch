
import requests
import pandas as pd
import time
import sys
import isodate



SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
CONFIG_FILE = "config.json"


def get_video_ids(query: str, API_KEY: str, max_results: int = 100):
    video_ids = []
    next_page_token = None

    while len(video_ids) < max_results:
        params = {
            "key": API_KEY,
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 50,
            "pageToken": next_page_token,
            "order": "relevance"
        }
        response = requests.get(SEARCH_URL, params=params).json()
        items = response.get("items", [])
        video_ids += [item["id"].get("videoId") for item in items if "videoId" in item["id"]]

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        time.sleep(1)

    return video_ids[:max_results]

def get_video_info(video_ids, API_KEY: str):
    results = []
    for i in range(0, len(video_ids), 50):
        ids_chunk = video_ids[i:i+50]
        params = {
            "key": API_KEY,
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(ids_chunk),
        }
        response = requests.get(VIDEO_URL, params=params).json()
        items = response.get("items", [])
        for item in items:
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            channel_id = snippet.get("channelId")
            if not channel_id:
                continue
            try:
                duration = content_details.get("duration", "")
                readable_duration = convert_duration(duration)
                results.append({
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "channel_id": channel_id,
                    "view_count": int(statistics.get("viewCount", 0)),
                    "published_at": snippet.get("publishedAt", ""),
                    "duration": readable_duration,
                    "video_id": item.get("id")
                })
            except Exception:
                continue
        time.sleep(1)
    return results

def get_subscriber_counts(channel_ids, api_key: str):
    subs_map = {}
    for i in range(0, len(channel_ids), 50):
        ids_chunk = channel_ids[i:i+50]
        params = {
            "key": api_key,
            "part": "statistics",
            "id": ",".join(ids_chunk),
        }
        response = requests.get(CHANNEL_URL, params=params).json()
        for item in response.get("items", []):
            try:
                subs = int(item["statistics"].get("subscriberCount", 0))
                subs_map[item["id"]] = subs
            except Exception:
                continue
        time.sleep(1)
    return subs_map

def classify_reaction(reaction_score):
    if reaction_score < 1:
        return "관심도 낮음"
    elif reaction_score < 2:
        return "평균 이하"
    elif reaction_score < 5:
        return "양호"
    elif reaction_score < 10:
        return "주목"
    elif reaction_score < 50:
        return "강한 반응"
    else:
        return "버즈 콘텐츠"

def format_number_korean(n):
    return f"{n:,}"  # 예: 10,500

def format_view_count_korean(n):
    parts = []
    if n >= 10000:
        만 = n // 10000
        if 만:
            parts.append(f"{만}만")
        n = n % 10000
    if n >= 1000:
        천 = n // 1000
        if 천:
            parts.append(f"{천}천")
        n = n % 1000
    if n >= 100:
        백 = n // 100
        if 백:
            parts.append(f"{백}백")
    return " ".join(parts) if parts else f"{n:,}"

def convert_duration(duration):
    try:
        td = isodate.parse_duration(duration)
        total_seconds = int(td.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분 {seconds}초"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"
    except:
        return "-"

def main(query: str, max_results: int = 100, api_key: str = "", return_df: bool = False):
    print(f"\n[INFO] \"{query}\" 검색 시작...")
    video_ids = get_video_ids(query, api_key, max_results=max_results)
    print(f"[INFO] 영상 ID {len(video_ids)}개 수집")

    video_info = get_video_info(video_ids, api_key)
    channel_ids = list({v["channel_id"] for v in video_info})
    print(f"[INFO] 채널 ID {len(channel_ids)}개 수집")
    if not channel_ids:
        print("[ERROR] 조건에 맞는 채널이 없습니다. 필터 조건을 완화해 보세요.")
        sys.exit(1)

    subs_map = get_subscriber_counts(channel_ids, api_key)

    filtered_info = []
    for video in video_info:
        subs = subs_map.get(video["channel_id"], 0)
        if subs >= 100:
            
            video["subscriber_count"] = subs
            video["subscriber_count_simple"] = format_number_korean(subs)
            video["view_simple"] = format_view_count_korean(video["view_count"])
            video["view_count_formatted"] = format_number_korean(video["view_count"])
            video["reaction_score"] = round(video["view_count"] / subs, 2) if subs > 0 else 0.0
            video["reaction_level"] = classify_reaction(video["reaction_score"])
            video["url"] = f"https://www.youtube.com/watch?v={video['video_id']}"
            video["thumbnail_url"] = f"https://img.youtube.com/vi/{video['video_id']}/hqdefault.jpg"
            filtered_info.append(video)

    if not filtered_info:
        print("[ERROR] 조건에 맞는 영상이 없습니다 (ex. 구독자 100명 이상).")
        sys.exit(1)

    df = pd.DataFrame(filtered_info)
    df_sorted = df.sort_values(by="reaction_score", ascending=False).head(100)
    df_sorted.drop(columns=["channel_id", "video_id", "view_count","subscriber_count"], inplace=True)
    df_sorted.rename(columns={
        "title": "제목",
        "channel_title": "채널명",
        "published_at": "업로드 날짜",
        # "view_count" : "조회수",
        "view_count_formatted": "조회수",
        "view_simple": "조회수 한글표현",
        "subscriber_count_simple": "구독자수",
        "reaction_score": "반응도 (조회수/구독자)",
        "reaction_level": "반응 해석",
        "duration": "영상 길이",
        "url": "영상 링크"
    }).to_csv(f"{query}_reaction_top.csv", index=False, encoding="utf-8-sig")
    print(f"[DONE] \"{query}_reaction_top.csv\" 파일 저장 완료")
    # if return_df:
    #     return df_sorted
    if return_df:
        return df_sorted.reset_index(drop=True), filtered_info  # ← video_id 등 원본도 함께 반환

if __name__ == "__main__":
    main("쿠파스")  # ◀ 원하는 검색어로 변경
