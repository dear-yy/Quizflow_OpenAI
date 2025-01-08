import openai
import time

# 함수 목록 
    # split_text
    # summarize_chunk
    # summarize_article


#기사 요약#
    # 텍스트 분할 함수
def split_text(text, max_chunk_size=3000):
    """
    긴 텍스트를 max_chunk_size 크기로 분할합니다.
    """
    chunks = []
    while len(text) > max_chunk_size:
        split_point = text.rfind('.', 0, max_chunk_size)  # 문장 단위로 자르기
        if split_point == -1:  # 마침표가 없는 경우 강제로 자름
            split_point = max_chunk_size
        chunks.append(text[:split_point + 1].strip())
        text = text[split_point + 1:].strip()
    chunks.append(text)
    return chunks


    # 텍스트 조각 단위 요약
def summarize_chunk(chunk, model="gpt-4o-mini", max_tokens=150):
    prompt = ( f"""
        다음 텍스트를 기반으로 전체 기사 내용을 요약하고 주요 정보를 포함하세요. 요약은 5~7개의 문장으로 작성해주세요.
        또한, 기사의 전체 맥락을 유지하며 핵심 내용을 간결히 정리하세요. 주요 내용을 이해하는 데 필요한 부가 설명은 포함하되, 불필요한 세부사항은 생략하세요.\n\n
        텍스트 조각: {chunk}
        """
    )
    while True:  # RateLimitError가 발생하면 재시도
        try:
            # Open API 호출
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0  # Temperature 설정
            )
            return response['choices'][0]['message']['content'].strip()

        except openai.error.RateLimitError:  
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)  # 40초 대기 후 재시도
            continue

        except Exception as e:
            return f"Error: {e}"



    # 최종 기사 요약_(연결된 조각을 요약)
def summarize_article(article_text):
    """
    긴 텍스트를 요약하는 함수입니다.
    """
    chunks = split_text(article_text)
    partial_summaries = [summarize_chunk(chunk) for chunk in chunks]

    # 최종 요약
    final_prompt = "다음 텍스트를 기반으로 전체 기사 내용을 요약하고 주요 정보를 포함세요. 또한, 기사의 전체 맥락을 유지하며 핵심 내용을 간결히 정리하세요. 주요 내용을 이해하는 데 필요한 부가 설명은 포함하되, 불필요한 세부사항은 생략하세요. 불필요한 세부사항이란, 기사의 제목과 주제와 가장 관련이 없는 부분을 말하는 것입니다. 변화 추이가 있을 경우, 직접적인 수의 나열보다는 단어로 표현하세요. 요약은 대략 10개의 문장으로 작성해주세요.(문장마다 줄바꿈 적용하기)" + "\n\n".join(partial_summaries)

    while True:  #RateLimitError가 발생하면 재시도
        try:
            # Open API 호출
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # 모델 명시적 정의
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes text."},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=1000,
                temperature=0  # Temperature 설정
            )
            return response['choices'][0]['message']['content'].strip()

        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)  # 40초 대기 후 재시도
            continue  

        except Exception as e:
            return f"Error: {e}"


