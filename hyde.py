import os
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수를 로드합니다.

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field # Pydantic import 추가
import chromadb


# crawled_data 구조: 
# {"before": before, "after": after}

class Fragments(BaseModel):
    """프로젝트의 가상 조각에 대한 정보를 담는 구조"""
    fragments: list[str] = Field(description="생성된 가상의 프로젝트 조각 리스트 5개")


search_prompt_template = ChatPromptTemplate.from_template(
"""
형식과 예시를 참고하여 이 크롤링 데이터의 보도자료의 영향을 받을 만한 "프로젝트"의 가상의 조각 5개를 생성하라.

[크롤링 데이터]:
{crawled_data}

["프로젝트"에 대한 설명]:
{description}

"""
)


# 가상 문서를 생성할 모델 정의
model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.8)


# 입력: {"collection": <CollectionObject>, "crawled_data": "..."}
# 출력: 가상 프로젝트 조각들 []

worker_chain = (
    RunnablePassthrough.assign(
        description=RunnableLambda(lambda x: x['collection'].metadata.get("description"))
    )
    | search_prompt_template
    | model.with_structured_output(Fragments)
    | RunnableLambda(
        lambda x: x.fragments
    )
)

# 입력: {"client": <Chroma client>, "crawled_data": "..."}
# 출력: [ "hyde_result":[가상프로젝트조각 * 5], "colection": collection, "crawled_data": crawled_data ]
HyDEchain = (
    RunnableParallel(
        crawled_data=RunnableLambda(lambda x: x["crawled_data"]),
        collections=RunnableLambda(lambda x: x["client"].list_collections())
    )

    # 콜렉션과 크롤링 데이터 쌍의 리스트로 변환
    # 입력: {"crawled_data": "...", "collections": [<collection>] }을 받기
    # 출력: [ {"collection": collection, "crawled_data": crawled_data} ]
    | RunnableLambda(
        lambda x: [
            {"collection": collection, "crawled_data": x["crawled_data"]}
            for collection in x["collections"]
        ]
    )

    # worker batch 하기
    # 출력: [ "hyde_result":[가상프로젝트조각 * 5], "colection": collection, "crawled_data": crawled_data ]
    | RunnableParallel(
       hyde_result= worker_chain,
       collection= RunnableLambda(lambda x: x["collection"]),
       crawled_data= RunnableLambda(lambda x: x["crawled_data"])
    ).map()
)

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
