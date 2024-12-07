# 터미널에서 설치!
# pip install openai==0.28
# pip install simplejson
# pip install python-dotenv


#main.py
import os
import sys
import urllib.request
import pandas as pd
import json
import re
import simplejson
import time
import openai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime


# 필요한 모듈과 함수들을 각 파일에서 가져오기
from selectArticle import (
    extract_keywords,
    Google_API,
    find_recommend_article,
    get_article_body,
    process_recommend_article
)

from summarizeArticle import (
    split_text,
    summarize_chunk,
    summarize_article
)

from multipleChoiceQuiz import (
    generate_multiple_choice_quiz_with_check,
    check_answer
)

from descriptiveQuiz import (
    generate_descriptive_quiz,
    evaluate_descriptive_answer
)


# .env 파일에서 환경 변수 로드인
load_dotenv()

# 환경 변수에서 키 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")  



###실행###
# 사용자에 학습하길 원하는 분야에 대한 입력을 요청
user_feedback = input("안녕하세요!\n🔍 어떤 주제에 대해 학습하고 싶으신가요? 입력해주시면 관련된 퀴즈로 안내드릴게요!\n >>")

# 퀴즈 시작을 알리는 메시지 출력
print("\n🎉퀴즈를 시작합니다! 최선을 다해보세요!✨")


wanted_row_per_site = 3 # 각 사이트당 결과 개수
sites = ["bbc.com",
         "khan.co.kr",
         "brunch.co.kr",
         "hani.co.kr",
         "ytn.co.kr",
         "sisain.co.kr",
         "news.sbs.co.kr",
         "h21.hani.co.kr" ,
         "ohmynews.com",
         ]
total_score =  0 #아티클 3개에 대한 총 점수
query_parts = []  # 쿼리를 구성할 부분들을 리스트로 저장
query = " ".join(query_parts) # 키워드 저장 배열

for k in range(3):
    #변수 정의
    total_score_for_the_article = 0 #현재 아티클에 대한 총점을 의미함

    print(f"\n\n\n\n================================================={k+1}번째 아티클=================================================")


    #키워드 추출
    extracted_keywords = extract_keywords(query, user_feedback, max_keywords=3)
    print("추출된 키워드:", extracted_keywords)


    #기사 검색어 설정
    query_parts.extend(extracted_keywords)  # 추출된 키워드 저장
    query_parts = list(set(query_parts))  # 중복쿼리 삭제
    query = " ".join(query_parts)
    print("최종 검색어:", query)
    print("\n")


    #article Search
    df = Google_API(query=query, wanted_row_per_site=wanted_row_per_site, sites=sites)#주어진 query(키워드)로 탐색된 기사 목록
    time.sleep(30)  # 30초 동안 프로그램이 멈춤 # 생성 토큰 제한 문제 예방


    # find recommended article
    info_for_the_article = process_recommend_article(df, user_feedback)
    recommend_article_body = info_for_the_article.iloc[0]['Body']  # URL 추출

    #기사 요약 출력
    article_summary = summarize_article(recommend_article_body)
    print("기사 최종 요약:")
    print(article_summary)
    print("\n\n")


    #객관식 2문제
    multiple_choice_score = 0
    previous_quiz = None  # 첫 번째 문제는 이전 문제 없음
    for i in range(2):  # 두 개의 문제 생성 및 확인
      if(i==0):
        print(f"\n[1️⃣문제]")
      else:
        print(f"\n[2️⃣문제]")

      quiz, correct_answer = generate_multiple_choice_quiz_with_check(article_summary, previous_quiz)
      if correct_answer is None:
          print("문제를 생성하는 데 오류가 발생했습니다. 다시 시도해 주세요.")
          break

      print(f"\n출제된 퀴즈:\n{quiz}")

      while True:  # 유효한 입력을 받을 때까지 반복
        try:
            user_answer = int(input("\n퀴즈 정답 번호를 입력하세요 (1~5): ").strip())  # 사용자 답변 입력
            if 1 <= user_answer <= 5:  # 입력값이 1~5 사이인지 확인
                score = check_answer(user_answer, correct_answer)
                multiple_choice_score += score

                if score > 0:
                    print("정답입니다! 2점을 획득하셨습니다.\n\n\n")
                else:
                    print(f"오답입니다! 실제 정답은 {correct_answer}번입니다. 점수는 0점입니다.\n\n\n")
                previous_quiz = quiz  # 첫 번째 문제를 저장해서 두 번째 문제에 반영
                break  # 유효한 입력이 들어왔으므로 루프 종료
            else:
                print("입력 값은 1~5 사이의 숫자여야 합니다. 다시 시도하세요.")
        except ValueError:
            print("유효하지 않은 입력입니다. 숫자 1~5 사이의 값을 입력하세요.")

    total_score_for_the_article += multiple_choice_score




    #서술형 문제
    print(f"\n[3️⃣문제]")
    quiz3, model_answer3 = generate_descriptive_quiz(article_summary) # 퀴즈 & 모범답안 생성
    print(f"출제된 퀴즈: \n{quiz3}\n")
    user_answer3 = input("퀴즈에 대한 답변을 입력하세요 (2문장 이내로 작성): \n") # 사용자 답변 입력
    print(f"\n모범 답안: \n{model_answer3}") # 모범 답변 출력

    evaluation3 = evaluate_descriptive_answer(user_answer3, quiz3, model_answer3) # 서술형 답안 평가 함수 호출
    total_score_for_the_article += evaluation3["total_score"] #서술형 점수

        #서술형 답안 평가 결과 출력
    print("💡기준별 피드백")
    for criterion, feedback in evaluation3["criteria"].items():
      print(f"  - {criterion}: {feedback}")
    print("\n💡종합 피드백")
    print(f"  - 이해도: {evaluation3['feedback']['understanding_feedback']}")
    print(f"  - 개선점: {evaluation3['feedback']['improvement_feedback']}")
        #서술형 점수
    print(f"\n서술형 점수: {evaluation3['total_score']}" + "/6\n")



    # 최종 점수 출력
    print(f"\n\n\n*****{k+1}번째 아티클 총점*****")
    print(f"{total_score_for_the_article}/10 \n")
    print(f"*****************************\n\n\n")
    total_score += total_score_for_the_article

    #사용자에게 해당 아티클에 대한 피드백 받기
    if(k<2):
      user_feedback = input("🔍 해당 아티클을 읽고 더 궁금한거나, 이해하기 어려운 부분에 대해 입력해주세요.\n(입력 내용은 다음 아티클 출제에 반영됩니다.)\n");
      print("\n\n");
      time.sleep(20)  # 20초 동안 프로그램이 멈춤



print("👏 훌륭합니다! 오늘의 퀴즈를 모두 마치셨습니다.")
print(f"📊 최종 점수: {total_score}/30")