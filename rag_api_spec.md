
# RAG API Specification

사내 RAG 시스템에서 문서를 **저장(Indexing)** 하고 **검색(Retrieval)** 하기 위한 API 명세입니다.

---

# 1. Cluster Health Check

Elasticsearch 클러스터 상태 확인 API

### 상태 종류

| 상태     | 설명                             |
| ------ | ------------------------------ |
| green  | 모든 노드 정상                       |
| yellow | 일부 replica 누락                  |
| red    | 원본 + replica 모두 누락 (데이터 유실 상태) |

---

# 2. Index Information

인덱스 상태, 크기, 문서 수 등을 조회합니다.

### Parameter

| 이름         | 타입     | 설명                      |
| ---------- | ------ | ----------------------- |
| index_name | string | 조회할 인덱스명 (와일드카드 `*` 가능) |

예시

```
rp-gocinfo-mail
rp-gocinfo-*
```

---

# 3. Document Indexing (문서 저장)

문서를 RAG 검색 인덱스에 추가합니다.

문서 추가 시 **자동으로 chunking**이 수행됩니다.

---

## Request Body

```json
{
  "index_name": "rp-some-index",
  "data": {
    "doc_id": "ABCD00001",
    "title": "예시 제목",
    "content": "예시 컨텐츠",
    "permission_groups": ["ds"],
    "created_time": "2025-05-29T17:03:00.242+09:00"
  },
  "chunk_factor": {
    "logic": "fixed_size",
    "chunk_size": 100,
    "chunk_overlap": 50,
    "separator": " "
  }
}
```

---

## Required Fields

| Field   | Type   | 설명       |
| ------- | ------ | -------- |
| doc_id  | string | 문서 고유 ID |
| title   | string | 문서 제목    |
| content | string | 문서 내용    |

---

## Optional Fields

| Field             | Type      | Default | 설명         |
| ----------------- | --------- | ------- | ---------- |
| permission_groups | list[str] | ["ds"]  | 조회 권한      |
| created_time      | string    | 현재 시간   | 문서 생성 시간   |
| url               | list[str] | -       | 원본 링크      |
| custom fields     | any       | -       | 자유롭게 추가 가능 |

---

## Chunking 옵션

| Field         | 설명                       |
| ------------- | ------------------------ |
| logic         | chunking 방식 (fixed_size) |
| chunk_size    | chunk 크기 (100 ~ 8000)    |
| chunk_overlap | chunk overlap (50 이상)    |
| separator     | 토큰 구분자                   |

### 규칙

```
100 <= chunk_size <= 8000
50 <= chunk_overlap < chunk_size
```

---

# 4. Vector Document Insert (이미 임베딩된 문서 저장)

이미 임베딩된 벡터를 직접 저장할 수도 있습니다.

Embedding Model: **BGE-M3**

---

## Request Example

```json
{
  "index_name": "rp-some-index",
  "data": {
    "doc_id": "ABCD00001",
    "chunk_id": "ABCD00001_000001",
    "title": "예시 제목",
    "merge_title_content": "예시 제목 <SEP> 컨텐츠 내용",
    "v_merge_title_content": [0.123, -0.234, 0.456],
    "permission_groups": ["ds"],
    "created_time": "2025-05-29T17:03:00.242+09:00"
  }
}
```

---

## Required Fields

| Field                 | 설명               |
| --------------------- | ---------------- |
| doc_id                | 문서 ID            |
| chunk_id              | chunk ID         |
| title                 | 문서 제목            |
| merge_title_content   | title + content  |
| v_merge_title_content | embedding vector |

---

# 5. BM25 Keyword Search

텍스트 기반 검색 (BM25)

---

## Request Parameters

| Parameter         | Required | Type | Default                   | 설명      |
| ----------------- | -------- | ---- | ------------------------- | ------- |
| index_name        | O        | str  | -                         | 검색할 인덱스 |
| query_text        | O        | str  | -                         | 검색어     |
| permission_groups | O        | list | -                         | 조회 권한   |
| num_result_doc    |          | int  | 5                         | 반환 문서 수 |
| fields_exclude    |          | list | ["v_merge_content_title"] | 제외 필드   |

---

# 6. Vector Search (KNN)

벡터 유사도 기반 검색

---

## Request Parameters

| Parameter         | Required | Type | Default |
| ----------------- | -------- | ---- | ------- |
| index_name        | O        | str  | -       |
| query_text        | O        | str  | -       |
| permission_groups | O        | list | -       |
| num_result_doc    |          | int  | 5       |
| filter            |          | json | {}      |

---

## Filter Example

```
{
  "creator_id": ["gildong.hong"],
  "tags": ["rag", "llm"]
}
```

조건

* 동일 필드 → OR
* 다른 필드 → AND

---

# 7. Hybrid Search (BM25 + KNN)

BM25와 Vector Search를 결합한 검색 방식

---

## Request Parameters

| Parameter         | Required | Type | Default |
| ----------------- | -------- | ---- | ------- |
| index_name        | O        | str  | -       |
| query_text        | O        | str  | -       |
| permission_groups | O        | list | -       |
| num_result_doc    |          | int  | 5       |
| filter            |          | json | {}      |

---

# 8. Weighted Hybrid Search

BM25와 KNN 가중치 조절 가능

---

## Request Parameters

| Parameter  | Type  | Default | 설명       |
| ---------- | ----- | ------- | -------- |
| bm25_boost | float | 0.025   | BM25 가중치 |
| knn_boost  | float | 7.98    | KNN 가중치  |

---

# 9. Field Match Search (BM25)

특정 필드 기반 검색

---

## Request Parameters

| Parameter  | Required | 설명       |
| ---------- | -------- | -------- |
| field      | O        | 검색 대상 필드 |
| query_text | O        | 검색어      |
| operator   |          | OR / AND |

---

# 10. Exact Match Search

특정 필드에 대해 정확히 일치하는 값 검색

---

## Parameters

| Parameter  | 설명        |
| ---------- | --------- |
| field      | 검색 대상 필드  |
| query_text | 정확히 일치할 값 |

---

# 11. Document Delete

문서 삭제 API

⚠ 삭제 후 복구 불가

---

## Request Parameters

| Parameter         | Type | 설명        |
| ----------------- | ---- | --------- |
| index_name        | str  | 인덱스 이름    |
| permission_groups | list | 권한        |
| doc_id            | str  | 삭제할 문서 ID |

---

# 12. Important Rules

### 문서 크기 제한

```
content < 1MB
merge_title_content < 1MB
```

---

### 특수문자 제거

검색 및 문서 저장 시 **특수문자 및 제어문자 제거 필요**

---

### Permission Groups

검색 시 문서는 **permission_groups 일치 조건**으로 필터링됩니다.

예

```
permission_groups = ["ds"]
```

---

# 13. Retrieval Best Practices

추천 검색 방식

```
Hybrid Search (BM25 + KNN)
```

이유

* 키워드 매칭
* 의미 기반 유사도

동시에 활용 가능

---

# 14. Example Query

```json
{
  "index_name": "rp-gocinfo-mail",
  "query_text": "HBM 이슈",
  "permission_groups": ["ds"],
  "num_result_doc": 10
}
```

---

# 15. Notes

* 모든 문서는 JSON 형식
* 검색 시 특수문자 제거 필요
* filter는 AND / OR 규칙 적용
* 임베딩 모델: **BGE-M3**

-------
예시

 

DS API HUB → go/apihub (https://api.samsungds.net) 에서 RAG API 구독 이후, 해당 페이지에서 발급
         DS Assistant > 3. RAG API 사용 방법 및 예제 > image-2025-6-13_14-22-53.png



RAG Portal → go/rag (https://rag.samsungds.net) 에서 우상단 톱니바퀴 모양 클릭 >> API 키 관리
           DS Assistant > 3. RAG API 사용 방법 및 예제 > image-2025-6-13_14-24-52.png

"prod" 및 "stg" 구분

RAG Portal (go/rag, https://rag.samsungds.net)에서 서비스 및 인덱스 생성하신 이후, DS API HUB의 "prod" API 사용해 주세요.

(DS API HUB의 "stg" API는 RAG Portal 개발계 (go/rag-stg, https://rag-stg.samsungds.net)와 연동됩니다.)



import requests
import json

url = "http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/index-info"

headers = {
    "Content-Type":  "application/json",
    "x-dep-ticket": {PASS_KEY},  # DS API HUB key
    "api-key": {RAG_KEY},  # RAG Portal key
}

params = {
  "index_name": {INDEX_NAME}
}

response = requests.request("GET", url, headers=headers, params=params)

print(response)
print(response.text)
<Response [200]>
[{"health":"green","status":"open","index":"rp-good-index","uuid":"i17q0f-wROO5I64A_5XdNA","pri":"1","rep":"1","docs.count":"57","docs.deleted":"5","store.size":"1.7mb","pri.store.size":"874.5kb","dataset.size":"874.5kb"}]

# formatting
[
  {
    "health": "green",
    "status": "open",
    "index": "rp-good-index",
    "uuid": "i17q0f-wROO5I64A_5XdNA",
    "pri": "1",
    "rep": "1",
    "docs.count": "57",
    "docs.deleted": "5",
    "store.size": "1.7mb",
    "pri.store.size": "874.5kb",
    "dataset.size": "874.5kb"
  }
]


import requests
import json


url = "http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/insert-doc"

headers = {
    "Content-Type":  "application/json",
    "x-dep-ticket": {PASS_KEY},  # DS API HUB key
    "api-key": {RAG_KEY},  # RAG Portal key
}

payload = {
    "index_name": "rp-rag-portal-admin-test-3",
    "data": {
        "doc_id": "ABCD00001",
        "title": "예시 제목",
        "content": "예시 컨텐츠",
        "permission_groups": [
            "rag-public"
        ],
        "created_time": "2025-05-29T17:02:54.917+09:00", # created_time 필드 없는 경우 현재 시간대로 등록
        "additionalField": "example_field_value"  # 커스텀 필드
    },
    "chunk_factor": {  #  chunk_factor 필드 없는 경우 기본값으로 적용
        "logic": "fixed_size",
        "chunk_size": 100,
        "chunk_overlap": 50,
        "separator": " "
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

print(response)
print(response.text)
※ payload의 필수 필드(index_name, data.doc_id, data.title, data.content) 미입력 시 422 에러 반환합니다.

<Response [200]>
[{"_index":"rp-some-index","_id":"ABCD00001_0","_score":3.1612465,"_source":{"doc_id":"ABCD00001","title":"예시 제목","permission_groups":["ds"],"created_time":"2025-07-11T15:10:32.087+09:00","additionalField":"example_field_value","chunk_id":"ABCD00001_0","merge_title_content":"예시 제목 [SEP] 예시 컨텐츠","statistics":{"byte_size":36,"token_count":7,"char_count":18},"indexed_time":"2025-07-23T10:23:12.610+09:00","modified_time":"2025-07-23T10:23:12.610+09:00","params":{"logic":"fixed_size","chunk_size":100,"chunk_overlap":50,"separator":" "},"doc_format":"text","creator_id":"-","source_subtype":"rp-some-index","indexed_from":"rag-api-v2","source_type":"ragaas"}}]

# formatting
[
  {
    "_index": "rp-some-index",
    "_id": "ABCD00001_0",
    "_score": 3.1612465,
    "_source": {
      "doc_id": "ABCD00001",
      "title": "예시 제목",
      "permission_groups": [
        "rag-public"
      ],
      "created_time": "2025-07-11T15:10:32.087+09:00",
      "additionalField": "example_field_value",
      "chunk_id": "ABCD00001_0",
      "merge_title_content": "예시 제목 [SEP] 예시 컨텐츠",
      "statistics": {
        "byte_size": 36,
        "token_count": 7,
        "char_count": 18
      },
      "indexed_time": "2025-07-23T10:23:12.610+09:00",
      "modified_time": "2025-07-23T10:23:12.610+09:00",
      "params": {
        "logic": "fixed_size",
        "chunk_size": 100,
        "chunk_overlap": 50,
        "separator": " "
      },
      "doc_format": "text",
      "creator_id": "-",
      "source_subtype": "rp-some-index",
      "indexed_from": "rag-api-v2",
      "source_type": "ragaas"
    }
  }
]
{
    "detail": [
        {
            "type": "missing",
            "loc": [    # 422 오류 발생 위치. body의 data의 doc_id를 뜻함.
                "body",
                "data",
                "doc_id" 
            ],
            "msg": "Field required",  # 오류 원인
            "input": {  # 오류 발생 부분의 사용자 입력값 (request body)
                "title": "타이틀 예제",
                "content": "본문 예제"
            }
        }
    ]
}


import requests
import json

url = "http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/retrieve-rrf"

headers = {
    "Content-Type":  'application/json',
    "x-dep-ticket": {PASS_KEY},  # DS API HUB key
    "api-key": {RAG_KEY},  # RAG Portal key
}

fields = {
    "index_name": {INDEX_NAME},
    "permission_groups" :['rag-public'],
    "query_text" : '반도체에 대해 알려주세요',
    "num_result_doc":5,
    "fields_exclude": [ "v_merge_title_content"],
    "filter": {
        "example_field_name": ["png"]
    }
}

json_data = json.dumps(fields)

response = requests.request("POST", url, data=json_data, headers=headers)
print(response)
print(response.text)
<Response [200]>
{"took":6,"timed_out":false,"_shards":{"total":1,"successful":1,"skipped":0,"failed":0},"hits":{"total":{"value":10,"relation":"eq"},"max_score":null,"hits":[{"_index":"rp-good-index","_id":"ABCD00002_1","_score":0.03226646,"_rank":1,"_source":{"doc_id":"ABCD00002","title":"반도체란 무엇일까요?","indexed_from":"rag-portal","created_time":"2025-05-02T09:00:00+09:00","creator_id":"dssl15214.id","permission_groups":["SSG_THIS_IS_A_TEST_GROUP_1","ds"],"source_type":"ragaas","url":["http://gspress.cauon.net","https://www.google.com"],"chunk_id":"ABCD00002_1","merge_title_content":"반도체란 무엇일까요? [SEP]  같은 규소 산화물들을 고온에서 여러 차례 정제해 순수한 규소의 순도를 높이고, 제조 공장에서 용도에 맞게 불순물의 비율을 조절하는 정밀한 가공을 거친 후 만들어진 거대한 실리콘 주괴를 얇게 절단해 제작한 실리콘 웨이퍼가 바로 대표적인 반도체다. 응용 분야는 매우 다양한데, 컴퓨터 부품인 시스템 반도체나 메모리 반도체뿐만 아니라 LED, LCD, OLED 등 디스플레이 소자와 태양전지도 모두 반도체로 만들어진다. 컴퓨터나 스마트폰에 들어가는 반도체 칩은 실리콘 웨이퍼 위에 필름 카메라 사진 현상과 유사한 제조 공정으로 복잡한 회로를 그려 넣어 제조한다. 제품별로 나눠보면 메모리 반도체와 비메모리 반도체로 나뉜다. 전자는 정보를 저장하고 기억하는 용도로 활용되며, D램과 낸드플래시 등이 이에 속한다. 후자는 메모리가 아닌 모든 제품을 말하며 이 ","statistics":{"byte_size":1055,"token_count":188,"char_count":439},"indexed_time":"2025-06-11T16:14:46.850434+09:00","params":{"logic":"fixed_size","chunk_size":100,"chunk_overlap":50,"separator":" "},"doc_format":"text","source_subtype":"rp-good-index"}}]}}

# formatting
{
  "took": 6,
  "timed_out": false,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 10,
      "relation": "eq"
    },
    "max_score": null,
    "hits": [
      {
        "_index": "rp-good-index",
        "_id": "ABCD00002_1",
        "_score": 0.03226646,
        "_rank": 1,
        "_source": {
          "doc_id": "ABCD00002",
          "title": "반도체란 무엇일까요?",
          "indexed_from": "rag-portal",
          "created_time": "2025-05-02T09:00:00+09:00",
          "creator_id": "dssl15214.id",
          "permission_groups": [
            "SSG_THIS_IS_A_TEST_GROUP_1",
            "ds"
          ],
          "source_type": "ragaas",
          "url": [
            "http://gspress.cauon.net",
            "https://www.google.com"
          ],
          "chunk_id": "ABCD00002_1",
          "merge_title_content": "반도체란 무엇일까요? [SEP]  같은 규소 산화물들을 고온에서 여러 차례 정제해 순수한 규소의 순도를 높이고, 제조 공장에서 용도에 맞게 불순물의 비율을 조절하는 정밀한 가공을 거친 후 만들어진 거대한 실리콘 주괴를 얇게 절단해 제작한 실리콘 웨이퍼가 바로 대표적인 반도체다. 응용 분야는 매우 다양한데, 컴퓨터 부품인 시스템 반도체나 메모리 반도체뿐만 아니라 LED, LCD, OLED 등 디스플레이 소자와 태양전지도 모두 반도체로 만들어진다. 컴퓨터나 스마트폰에 들어가는 반도체 칩은 실리콘 웨이퍼 위에 필름 카메라 사진 현상과 유사한 제조 공정으로 복잡한 회로를 그려 넣어 제조한다. 제품별로 나눠보면 메모리 반도체와 비메모리 반도체로 나뉜다. 전자는 정보를 저장하고 기억하는 용도로 활용되며, D램과 낸드플래시 등이 이에 속한다. 후자는 메모리가 아닌 모든 제품을 말하며 이 ",
          "statistics": {
            "byte_size": 1055,
            "token_count": 188,
            "char_count": 439
          },
          "indexed_time": "2025-06-11T16:14:46.850434+09:00",
          "params": {
            "logic": "fixed_size",
            "chunk_size": 100,
            "chunk_overlap": 50,
            "separator": " "
          },
          "doc_format": "text",
          "source_subtype": "rp-good-index"
        }
      },
      ...
    ]
  }
}


import requests
import json

url = "http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/delete-doc"

headers = {
    "Content-Type":  'application/json',
    "x-dep-ticket": {PASS_KEY},  # DS API HUB key
    "api-key": {RAG_KEY},  # RAG Portal key
}

fields= {
    "index_name": {INDEX_NAME},
    "permission_groups" :['rag-public'],
    "doc_id":'0000ABCD',
}
data = json.dumps(fields)

response = requests.request("POST", url, headers=headers, data=data)
print(response.text)
<Response [200]>
{"took":23,"timed_out":false,"total":1,"deleted":1,"batches":1,"version_conflicts":0,"noops":0,"retries":{"bulk":0,"search":0},"throttled_millis":0,"requests_per_second":-1.0,"throttled_until_millis":0,"failures":[]}

# formatting
{
  "took": 23,
  "timed_out": false,
  "total": 1,
  "deleted": 1,
  "batches": 1,
  "version_conflicts": 0,
  "noops": 0,
  "retries": {
    "bulk": 0,
    "search": 0
  },
  "throttled_millis": 0,
  "requests_per_second": -1.0,
  "throttled_until_millis": 0,
  "failures": []
}




curl -X GET http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/index-info?index_name={index_name} \
-H 'x-dep-ticket: {PASS-KEY}' \
-H 'api-key: RAG-API-KEY'


curl -X POST http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/insert-doc \
-H 'Content-Type: application/json' \
-H 'x-dep-ticket: PASS-KEY' \
-H 'api-key: RAG-API-KEY' \
  -d '{
  "index_name": "rp-rag-portal-admin-test-3",
  "data": {
    "doc_id": "ABCD00001",
    "title": "예시 제목",
    "content": "예시 컨텐츠",
    "permission_groups": [
      "rag-public"
    ],
    "created_time": "2025-05-29T17:02:54.917+09:00",
    "additionalProp1": "DFDFS"
  },
  "chunk_factor": {
    "logic": "fixed_size",
    "chunk_size": 100,
    "chunk_overlap": 50,
    "separator": " "
  }
}'


curl -X POST http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/retrieve-rrf \
-H 'Content-Type: application/json' \
-H 'x-dep-ticket: PASS-KEY' \
-H 'api-key: RAG-API-KEY' \
-d '{ 
   "index_name": "index_name",
   "query_text": "검색할 텍스트",
   "num_result_doc": 5,
   "permission_groups": ["rag-public" ],
   "fields_exclude": [ "v_merge_title_content"] ,
   "filter": {}
}'


curl -X POST http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2/delete-doc \
-H 'Content-Type: application/json' \
-H 'x-dep-ticket: PASS-KEY' \
-H 'api-key: RAG-API-KEY' \
-d '{
  "index_name": "index_name",
  "doc_id": "doc_id",
  "permission_groups": ["rag-public"]
}'




 
