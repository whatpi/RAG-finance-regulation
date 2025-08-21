from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import chromadb

model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.6)

alarm_prompt = ChatPromptTemplate.from_template(
"""
다음 규제 갱신 사항을 근거로 사용자에게 이 프로젝트의 수정해야할 점을 일목요연하게 설명하라

네가 엄격하게 판단하기에 

만약 수정할 필요가 없다고 느껴진다면, 오로지 '수정 필요 없음'라고만 출력하라

규제 갱신 설명: {crawled_data}

프로젝트 설명: {collection_description}

번들 요약: {bundle_summary}

실제 문서: {document}

"실제 문서"가 네가 규제 적용 검토를 해봐야할 문서다

"""
)


# 입력
# {
# "document": doc,
# "bundle_summary": summary,
# "collection_description": x["collection"].metadata.get("description"),
# "crawled_data": x["crawled_data"]
# }
single_prompt_chain = (
    alarm_prompt
    | model
    | StrOutputParser()
)


# 입력: {"ranked_result_sample": [(doc,해당 번들 서머리)*상위 10퍼센트],  "collection": collection, "crawled_data": "..."}
main_arlarm_chain_every_collection = (
    RunnableLambda(
        lambda x: [
            {"document": doc,
             "bundle_summary": summary,
             "collection_description": x["collection"].metadata.get("description"),
             "crawled_data": x["crawled_data"]
            }
            for doc, summary in x["ranked_result_sample"]
        ]
    )
    | single_prompt_chain.map()
)

