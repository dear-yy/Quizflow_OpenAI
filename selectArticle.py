import openai
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import json

#키워드 추출
"""
    Parameters:
        query (str): 기본 검색어. 사용자의 피드백이 비어 있을 경우 사용.
        user_feedback (str): 사용자가 입력한 텍스트.
        max_keywords (int): 반환할 최대 키워드 수. 기본값은 3.

    Returns:
        list: 추출된 SEO 키워드 리스트.
"""

def extract_keywords(query, user_feedback, max_keywords=3):
    try:
        # GPT에 전달할 역할 설명
        role_description = f"""
        # 역할
        당신은 SEO(검색 엔진 최적화)에 최적화된 키워드를 생성하는 역할을 합니다.
        - 사용자 피드백에서 검색 가능성을 극대화하는 핵심 키워드를 추출하세요.
        - 만약 사용자 피드백이 없다면 쿼리를 사용해 키워드를 생성하세요.

        # 키워드 추출 규칙
        1. **핵심 의미**:
        - 검색 엔진에서 자주 검색될 가능성이 높은 단어를 선택하세요.
        - 명사 중심의 구체적이고 직관적인 키워드를 사용하세요.
        - 동일한 단어를 가진 키워드는 통합합니다.
        - 중복된 키워드가 없어야 합니다.
        - 쿼리를 사용해 생성한 키워드는 쿼리와 동일하면 안 됩니다.
        2. **형식**:
        - 키워드의 개수>1 && 키워드의 개수 <=3
        3. **출력 형식**:
        JSON 형식으로 반환하세요:
        ```json
        ["키워드1", "키워드2", ...]
        ```
        """

        # GPT 호출
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": role_description
                },
                {
                    "role": "user",
                    "content": f"사용자 피드백: {user_feedback}\n쿼리: {query}\n\n사용자 피드백과 관련된 키워드를 생성해주세요. 만약 사용자 피드백이 없다면, 쿼리와 관련된 키워드를 생성해주세요. 생성된 키워드는 쿼리와 동일하면 안 됩니다."

                }
            ],
            temperature=0,
            max_tokens=50,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # GPT의 응답에서 키워드 추출
        keywords_json = response['choices'][0]['message']['content']

        # JSON 부분만 추출
        start_idx = keywords_json.find("[")
        end_idx = keywords_json.find("]") + 1

        if start_idx != -1 and end_idx != -1:
            keywords_json = keywords_json[start_idx:end_idx]

        try:
            # JSON 형식으로 응답을 파싱
            keywords = json.loads(keywords_json)
            # 중복 키워드 제거 및 최대 max_keywords로 제한
            unique_keywords = list(dict.fromkeys(keywords))[:max_keywords]
            return unique_keywords

        except json.JSONDecodeError:
            print(f"Error decoding JSON: {keywords_json}")
            return []
        except openai.error.RateLimitError:
          print("Rate limit reached. Retrying in 30 seconds...")
          time.sleep(30)

    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return []
    except openai.error.RateLimitError:
        print("Rate limit reached. Retrying in 30 seconds...")
        time.sleep(30)



#기사 서치#
Google_SEARCH_ENGINE_ID = "c00dbc74a71f84529"
Google_API_KEY = "AIzaSyAI2DG_1wQxrve0S4qQTOcTPaT_UXAI2Os"

# wanted_row_per_site = 3 # 각 사이트당 결과 개수
# sites = ["bbc.com",
#          "khan.co.kr",
#          "brunch.co.kr",
#          "hani.co.kr",
#          "ytn.co.kr",
#          "sisain.co.kr",
#          "news.sbs.co.kr",
#          "h21.hani.co.kr" ,
#          "ohmynews.com",
#          ]

def Google_API(query, wanted_row_per_site, sites):
    # 각 사이트의 결과를 모으기 위한 리스트
    df_google_list = []

    for site_index, site in enumerate(sites):  # 사이트 순서에 따라 번호 부여
        # 각 사이트별로 검색어를 구성
        site_query = f"site:{site} {query}"
        collected_results = 0  # 현재 사이트에서 수집한 결과 수
        start_index = 1  # 검색 시작 위치

        while collected_results < wanted_row_per_site:
            # URL 생성 및 요청
            url = f"https://www.googleapis.com/customsearch/v1?key={Google_API_KEY}&cx={Google_SEARCH_ENGINE_ID}&q={site_query}&start={start_index}&num=10"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    print(f"Error: {response.status_code}, Message: {response.text}")
                    break

                data = response.json()
                search_items = data.get("items")
                if not search_items:
                    print(f"No more results found for site {site}.")
                    break

                for search_item in search_items:
                    if collected_results >= wanted_row_per_site:
                        break

                    link = search_item.get("link")
                    title = search_item.get("title")
                    description = search_item.get("snippet")  # description 필드 추가

                    # 추가 조건: m.khan.co.kr 처리
                    if site == "khan.co.kr" and "m.khan.co.kr" in link:
                        link = link.replace("m.khan.co.kr", "khan.co.kr")

                    # 새로운 DataFrame 생성 후 리스트에 추가
                    df_google_list.append(pd.DataFrame(
                        [[title, description, link, site]],
                        columns=['Title', 'Description', 'Link', 'Domain']
                    ))
                    collected_results += 1

                # 다음 페이지 검색
                start_index += 10

            except Exception as e:
                print(f"Error occurred for site {site}: {e}")
                break

    # 모든 사이트의 결과를 하나의 DataFrame으로 결합
    df_google = pd.concat(df_google_list, ignore_index=True) if df_google_list else pd.DataFrame(columns=['Title', 'Description', 'Link', 'Domain'])
    return df_google







#추천 아티클 결정#
def find_recommend_article(df_google, user_feedback):
    # 아티클 목록에 index 포함
    article_titles = df_google['Title'].tolist()
    article_descriptions = df_google['Description'].tolist()
    article_indices = df_google.index.tolist()  # DataFrame의 index를 리스트로 저장

    # OpenAI API 호출
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "# 지시문\n"
                    "당신은 사용자의 피드백과 아티클의 제목 및 설명을 기반으로 "
                    "사용자에게 적합한 아티클을 추천하는 어플리케이션의 역할을 한다.\n"
                    "# 추천 조건\n"
                    "1. 사용자 피드백의 질문이나 요청에 답변이 될 수 있는 아티클이어야 한다.\n"
                    "2. 단순 뉴스 보도, 광고성 내용, 또는 중복된 내용은 제외해야 한다.\n"
                    "3. 구체적인 주제를 포함하고 있어야 한다.\n"
                    "4. 사용자의 피드백과 가장 관련성이 높은 내용을 다루는 아티클이어야 한다.\n"
                    "5. 제목이 명확하지 않을 경우, 설명을 중심으로 판단한다.\n"
                    "6. 지식적인 설명 또는 학습에 도움을 줄 수 있는 내용이 포함되어야 한다.\n"
                    "# 출력 형식\n"
                    "당신의 답변을 항상 다음 형식의 JSON으로 작성하세요:\n"
                    "{\n"
                    "  \"index\": \"추천된 아티클의 고유 index\",\n"
                    "  \"reason\": \"왜 이 아티클이 적합한지 간단히 설명\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": (
                    f"사용자 피드백: {user_feedback}\n\n"
                    "아티클 목록 (index 포함):\n"
                    + "\n".join(
                        f"{i}. [Index: {idx}] 제목: {title}\n   설명: {description}\n  "
                        for i, (idx, title, description) in enumerate(
                            zip(article_indices, article_titles, article_descriptions)
                        )
                    )
                )
            }
        ],
        temperature=0,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # GPT 응답에서 JSON 데이터 추출
    raw_content = response["choices"][0]["message"]["content"].strip("```json").strip("```").strip()
    try:
        response_json = json.loads(raw_content)
    except json.JSONDecodeError:
        print("GPT 응답이 JSON 형식이 아닙니다. 다시 요청하세요.")
        return pd.DataFrame()

    # index 검증
    if "index" not in response_json or "reason" not in response_json:
        print("GPT 응답에서 index 또는 reason이 누락되었습니다.")
        return pd.DataFrame()

    try:
        recommended_index = int(response_json["index"])  # index를 정수로 변환
    except ValueError:
        print("GPT가 반환한 index가 숫자가 아닙니다. 다시 요청하세요.")
        return pd.DataFrame()

    # index가 DataFrame에 존재하는지 확인
    if recommended_index not in df_google.index:
        print(f"추천된 index({recommended_index})가 데이터베이스에 없습니다.")
        return pd.DataFrame()

    # 추천 이유 출력
    print(f"추천된 이유: {response_json['reason']}")

    # 해당 index로 행 반환
    recommended_article = df_google.loc[[recommended_index]]
    return recommended_article







#본문 추출#
SITE_CLASS_MAPPING = {
    'bbc.com': [{'tag': 'main', 'class': 'bbc-fa0wmp'}],
    'khan.co.kr': [{'tag': 'div', 'class': 'art_body'}],
    'brunch.co.kr': [{'tag': 'div', 'class': 'wrap_body'}],
    'hani.co.kr': [{'tag': 'div', 'class': 'article-text'}],
    'ytn.co.kr': [{'tag': 'div', 'class': 'vodtext'}],
    'sisain.co.kr': [{'tag': 'div', 'class': 'article-body'}],
    'news.sbs.co.kr': [{'tag': 'div', 'class': 'main_text'}],
    'h21.hani.co.kr': [{'tag': 'div', 'class': 'arti-txt'}],
    'ohmynews.com': [
        {'tag': 'article', 'class': 'article_body at_contents article_view'},
        {'tag': 'div', 'class': 'news_body'}
    ],
    # 공백 주의
    # 추가 도메인 및 태그/클래스 매핑
    # 한국일보, mbcnews는 제외
}

def get_article_body(url, domain):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }

    try:
        # URL에서 HTML 가져오기
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 도메인이 제공된 경우 SITE_CLASS_MAPPING에서 처리
        site_info = SITE_CLASS_MAPPING.get(domain)
        if not site_info:
            return f"도메인 {domain}에 대한 정보가 없습니다."

        # 모든 매핑 리스트 순회하며 태그/클래스 처리
        for mapping in site_info:
            tag_name = mapping.get('tag')
            class_name = mapping.get('class')
            main_body = soup.find(tag_name, class_=class_name)
            if main_body:
                # 태그 내부에 p, h1 등이 있는 경우와 없는 경우 처리
                text_elements = main_body.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li'])

                # <p> 태그 개수 확인 (2개 이하이면 본문이 부족하다고 간주)
                paragraph_count = len(main_body.find_all('p'))
                if paragraph_count <= 2:
                    return main_body.get_text(strip=True)

                if text_elements:
                    return "\n".join([element.get_text(strip=True) for element in text_elements])
                else:
                    return main_body.get_text(strip=True)
        return f"'{domain}'에 대한 매핑된 태그와 클래스를 찾을 수 없습니다."

    except requests.exceptions.RequestException as e:
        return f"HTTP 요청 중 오류 발생: {e}"
    except Exception as e:
        return f"본문 추출 중 오류 발생: {e}"
    




#추천된 아티클에서 URL, Domain, Title을 추출
def process_recommend_article(df=None, user_feedback=""):
    # 초기화: find
    recommend_article = pd.DataFrame(columns=['Title', 'URL', 'Body'])
    recommend_article = find_recommend_article(df, user_feedback)

    # 추천 프로세스
    while True:
        # 추천된 아티클이 비어 있는 경우 루프 종료
        if recommend_article.empty:
            print("추천된 아티클이 더 이상 없습니다.")
            return pd.DataFrame(columns=['Title', 'URL', 'Body'])  # 빈 DataFrame 반환

        try:
            # URL, Domain, Title 추출
            url = recommend_article.iloc[0]['Link']  # URL 추출
            domain = recommend_article.iloc[0]['Domain']  # Domain 추출
            title = recommend_article.iloc[0]['Title']  # Title 추출
        except IndexError as e:
            print(f"추천된 아티클에서 데이터를 추출할 수 없습니다: {e}")
            print("해당 아티클을 추천 목록과 전체 데이터프레임에서 삭제합니다...")

            # recommend_article에서 삭제
            recommend_article.drop(recommend_article.index[0], inplace=True)
            # df에서 삭제
            df.drop(df[df['Link'] == url].index, inplace=True)
            # 새로운 추천 아티클 요청
            recommend_article = find_recommend_article(df, user_feedback)
            continue

        # 본문(article body) 추출
        article_body = get_article_body(url=url, domain=domain)  # 본문 추출 함수 호출

        # 본문이 없거나 본문 길이가 5문장 이하인 경우 처리
        if not article_body or len([s for s in article_body.split('.') if s.strip()]) <= 5:
            print(f"본문이 없는 아티클 (또는 본문이 5문장 이하): {title} - {url}")
            print("해당 아티클을 추천 목록과 전체 데이터프레임에서 삭제합니다...")

            # recommend_article에서 삭제
            recommend_article.drop(recommend_article.index[0], inplace=True)

            # df에서 삭제
            df.drop(df[df['Link'] == url].index, inplace=True)

            # 새로운 추천 아티클 요청
            recommend_article = find_recommend_article(df, user_feedback)
            continue  # 새로 추천된 아티클로 루프 재시작

        # 본문이 유효할 경우 DataFrame 생성 및 반환
        info_for_the_article = pd.DataFrame({
            'Title': [title],
            'URL': [url],
            'Body': [article_body]
        })
        return info_for_the_article
