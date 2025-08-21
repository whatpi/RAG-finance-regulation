import os
from dotenv import load_dotenv

load_dotenv()

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers.cross_encoder import CrossEncoder
import math

reranker_model = CrossEncoder('Qwen/Qwen3-Reranker-0.6B')

# 한 개의 콜렉션 -> hyde * 5 -> summary * 35 -> bundle id set -> 해당 bundle_id의 fragment 출력물들을 reranking
# 입력: { "crawled_data": "...", "fragment_documents": [frag_chromadb_value] }
# 출력: [doc * 상위 10퍼센트]
def rerank_fragments(inputs, top_ratio=0.6):
    # 질문 형태로 고치기
    question = f'{inputs["crawled_data"]} 이러한 규제사항 변경의 영향을 받을만한 회사의 프로젝트를 찾아줘'
    fragment_results = inputs["fragment_results"]
    docs = fragment_results.get("documents", [])

    if not docs:
        return []
    
    metadatas = fragment_results.get("metadatas", [])

    if not docs or not metadatas:
        return []
    
    doc_bundle_ids = [meta.get("bundle_id") for meta in metadatas]
    
    num = len(docs)
    top_k = math.ceil(num*top_ratio)
    # 순서쌍 모음으로 고치기
    pairs = [(question, doc) for doc in docs]
    # 점수 생성
    scores = reranker_model.predict(pairs, batch_size=1)
    # doc 인덱싱 포함
    ranked_result = list(zip(docs, scores, doc_bundle_ids))
    # 정렬
    ranked_result.sort(key=lambda x: x[1], reverse=True)
    print(ranked_result)

    sample = ranked_result[:top_k]

    sample_bundle_ids = [id for _, __, id in sample]

    summary_results = summary_by_bundle_ids(inputs["collection"], sample_bundle_ids)

    summary_by_bundle_ids_map = {
        meta["bundle_id"]: summary
        for meta, summary in zip(summary_results["metadatas"], summary_results["documents"])
    }

    result = [(doc, summary_by_bundle_ids_map[id]) for doc, _, id in sample]

    # return
    return result

# collection에 쿼리 날리기
# 입력: [ "hyde_result":[가상프로젝트조각 * 5], "collection": collection, "crawled_data": crawled_data ]
# 출력: summary_result ( chromadb 쿼리 )
# documents = [[hyde-doc*7]*5]
def query_collection_summary(inputs):
    summary_results = inputs["collection"].query(
                query_texts=inputs["hyde_result"],
                n_results=7,
                where={"doc_type": "summary"}
            )
    
    return summary_results

# 입력: {"summary_result", "collection"}
def query_fragment_by_summary(inputs):
    # metadata 평탄화
    flatten_metadatas = [metadata for sublist in inputs["summary_results"]["metadatas"] if sublist for metadata in sublist]

    if not flatten_metadatas:
        return []
    
    # 번들 아이디 추출
    bundle_ids = list(set(meta["bundle_id"] for meta in flatten_metadatas if 'bundle_id' in meta))

    if not bundle_ids:
        return []
    
    fragment_results = inputs["collection"].get(
        where={
            "$and": [
                {"doc_type": {"$eq": "fragment"}},
                {"bundle_id": {"$in": bundle_ids}}
            ]
        }
    )

    return fragment_results

def summary_by_bundle_ids(col, bundle_ids):
    documents = col.get(
        where={"$and": [
                {"bundle_id": {"$in": bundle_ids}},
                {"doc_type": {"$eq": "summary"}}
            ]
        },
        include=["documents", "metadatas"]
    )
    return documents

# 입력: "hyde_result":[가상프로젝트조각 * 5], "collection": collection, "crawled_data": crawled_data
# 출력: {"ranked_result_sample": [(doc,해당 번들 서머리)*상위 10퍼센트],  "collection": collection, "crawled_data": "..."}
single_query_chain = (
    RunnablePassthrough.assign(
        summary_results=RunnableLambda(query_collection_summary),
    )
    | RunnablePassthrough.assign(
        fragment_results=RunnableLambda(query_fragment_by_summary),
    )
    | RunnablePassthrough.assign(
        ranked_result_sample=RunnableLambda(rerank_fragments),
    )
    | RunnableParallel(
        ranked_result_sample=RunnableLambda(lambda x: x["ranked_result_sample"]),
        collection=RunnableLambda(lambda x: x["collection"]),
        crawled_data=RunnableLambda(lambda x: x["crawled_data"]),
    )
)