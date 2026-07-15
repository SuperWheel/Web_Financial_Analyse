# Design 009

## 模块

```
services/fetching/
  http_util.py     # 共享 Client 头、下载 PDF 校验
  cninfo.py        # resolve_stock / search_annual_reports
  service.py       # download_url_to_job / search / download_candidate
import_service.create_job_from_upload(..., source_type=, hints=)
```

## 巨潮

1. `POST .../topSearch/query` keyWord=code → orgId, type, zwjc  
2. column：`sh*`→sse，`sz*`→szse，`bj*`→bse  
3. `POST .../hisAnnouncement/query` stock=`{code},{orgId}` category=`category_ndbg_szsh;` seDate=`{year}-01-01~{year+1}-12-31`  
4. PDF：`https://static.cninfo.com.cn/{adjunctUrl}`

## 限速

进程内简单间隔（默认 0.4s）；错误不重试轰炸。
