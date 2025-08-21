
import os
import asyncio
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수를 로드합니다.

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
import chromadb

from hyde import HyDEchain, worker_chain
from query import single_query_chain
from alarm import main_arlarm_chain_every_collection

client = chromadb.PersistentClient(path="project_db")

# main_chain = (
#     RunnableParallel.assign(
#         client=client
#     )
#     | HyDEchain
#     | (
#         single_query_chain
#        |main_arlarm_chain_every_collection
#       ).abatch
# )

data = """
{
  "regulation_id": "EFT_2024_001",
  "title": "전자금융거래법 시행령 일부개정안",
  "announcement_date": "2024-08-15",
  "effective_date": "2024-11-15",
  "source_url": "https://www.fsc.go.kr/no010101/79251",
  "main_changes": [
    {
      "article": "제10조의3(본인확인 강화)",
      "before": "1일 100만원 이상 이체 시 추가인증",
      "after": "1일 50만원 이상 이체 시 추가인증 의무화, 생체인증 또는 2채널 인증 필수",
      "impact_level": "HIGH"
    },
    {
      "article": "제15조의2(이상거래 탐지시스템)",
      "before": "FDS 시스템 권고사항",
      "after": "실시간 이상거래 탐지시스템(FDS) 구축 의무화, 24시간 모니터링 체계 필수",
      "requirement": "머신러닝 기반 이상거래 패턴 분석 기능 포함"
    },
    {
      "article": "제23조(고객정보 보호)",
      "before": "개인정보 암호화 저장",
      "after": "금융거래정보 암호화 강화(AES-256 이상), 접근권한 세분화, 접속기록 2년 보관 의무",
      "penalty": "위반 시 과태료 5천만원"
    }
  ],
  "compliance_deadline": "2024-11-14",
  "regulatory_body": "금융위원회"
}
"""

per_collection_chain = (
    RunnablePassthrough.assign(
        hyde_result=worker_chain
    )
    # {"collection":..., "crawled_data":..., "hyde_result":...}
    | single_query_chain
    | main_arlarm_chain_every_collection
)

main_chain = (
    RunnablePassthrough.assign(
        collections=RunnableLambda(lambda x: client.list_collections())
    )
    # [{"collection": col1, "crawled_data":...}]
    | RunnableLambda(
        lambda x: [
            {"collection": collection, "crawled_data": x["crawled_data"]}
            for collection in x["collections"]
        ]
    )
    # per_collection_chain 병렬 실행
    | per_collection_chain.abatch
)



async def run_async_chain():
    print("파이프라인 실행 시작...")
    results = await main_chain.ainvoke({"crawled_data": data})
    
    print("\n 파이프라인 실행 완료")
    # 결과 출력 (리스트의 리스트 형태일 수 있음)
    for i, collection_result in enumerate(results):
        print(f"\n--- 컬렉션 {i+1} 결과 ---")
        if not collection_result:
            print("처리할 내용 없음.")
        else:
            for alarm in collection_result:
                print(alarm)
                print("-" * 20)


if __name__ == "__main__":
    if not client.list_collections():
        print("ChromaDB에 데이터가 없습니다")
    else:
        asyncio.run(run_async_chain())

