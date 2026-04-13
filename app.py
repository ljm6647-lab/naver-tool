import streamlit as st
import re

st.title("예약 정리기")

naver_text = st.text_area("네이버")
phone_text = st.text_area("전화")


# -------------------------------
# 장소 추출 함수 (🔥 핵심)
# -------------------------------
def extract_place(line):
    # 1️⃣ 휘닉스 예외
    if "휘닉스" in line:
        return "그네"

    # 2️⃣ "OO로 픽업"
    m = re.search(r"([가-힣A-Za-z]+?)(?:로|에서)\s*픽업", line)
    if m:
        return m.group(1)

    # 3️⃣ "OO 픽업 요청"
    m = re.search(r"([가-힣A-Za-z]+)\s*픽업", line)
    if m:
        return m.group(1)

    # 4️⃣ fallback (마지막 단어 추정)
    words = re.findall(r"[가-힣A-Za-z]+", line)
    if words:
        return words[-1]

    return ""


# -------------------------------
# 네이버 파싱
# -------------------------------
def parse_naver(text):
    results = []
    blocks = re.split(r"\n\s*\n", text.strip())

    for b in blocks:
        lines = b.split("\n")

        time = ""
        people = ""
        phone = ""
        label = ""
        is_pickup = False
        place = ""

        for line in lines:
            line = line.strip()

            # 전화번호
            ph = re.search(r"010[-\s]?(\d{4})[-\s]?(\d{4})", line)
            if ph:
                phone = f"010-{ph.group(1)}-{ph.group(2)}"

            # 시간 (24시간 변환 안함)
            t = re.search(r"(\d{1,2}):(\d{2})", line)
            if t:
                time = f"{int(t.group(1)):02d}:{int(t.group(2)):02d}"

            # 인원
            p = re.search(r"전체\s*(\d+)", line)
            if p:
                people = f"{p.group(1)}명"

            # 픽업
            if "픽업" in line or "픽드랍" in line:
                is_pickup = True
                place = extract_place(line)

        if is_pickup:
            label = f"{place} 🚗" if place else "🚗"

        if time:
            results.append({
                "time": time,
                "people": people,
                "label": label,
                "phone": phone
            })

    return results


# -------------------------------
# 전화 파싱
# -------------------------------
def parse_phone(text):
    results = []
    blocks = re.split(r"\n\s*\n", text.strip())

    for b in blocks:
        lines = b.split("\n")

        time = ""
        people = ""
        phone = ""
        label = ""

        for line in lines:
            line = line.strip()

            # 시간
            t = re.search(r"(\d{1,2})시\s*(\d{1,2})?", line)
            if t:
                h = int(t.group(1))
                m = int(t.group(2)) if t.group(2) else 0
                time = f"{h:02d}:{m:02d}"

            # 인원
            p = re.search(r"\d+명", line)
            if p:
                people = p.group()

            # 전화번호
            ph = re.search(r"010\s*(\d{4})\s*(\d{4})", line)
            if ph:
                phone = f"010 {ph.group(1)} {ph.group(2)}"

            # 이름 + 🚗
            if "🚗" in line:
                label = line.replace(people, "").strip()

        if time:
            results.append({
                "time": time,
                "people": people,
                "label": label,
                "phone": phone
            })

    return results


# -------------------------------
# 정렬
# -------------------------------
def sort_all(data):
    return sorted(data, key=lambda x: int(x["time"][:2]) * 60 + int(x["time"][3:]))


# -------------------------------
# 실행
# -------------------------------
if st.button("정리하기"):

    data = []
    data += parse_naver(naver_text)
    data += parse_phone(phone_text)

    data = sort_all(data)

    output = ""

    for d in data:
        output += f"{d['time']}\n"
        output += f"{d['people']}"
        if d["label"]:
            output += f" {d['label']}"
        output += f"\n{d['phone']}\n\n"

    st.success("완료")
    st.text_area("결과", output, height=400)