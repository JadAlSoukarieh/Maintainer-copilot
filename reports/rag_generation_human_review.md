# RAG Generation Human Review

This report is a review helper for the five manually spot-checkable generation examples.
It does not change labels automatically.

## Manual steps

1. Read each example below.
2. Edit `data/rag/golden/rag_generation_human_labels.jsonl` directly.
3. Update these fields when you have actually reviewed the row:
   - `human_faithful`
   - `human_relevant`
   - `review_status`
   - `human_notes`
4. Only change `review_status` to `human_spot_checked` after a real manual review.
5. Re-run `python evals/rag_generation_eval.py` after editing labels.

Eval source: `reports/rag_generation_eval_report.json`

## rag-golden-001

**Question**  
How does `stream.pipeline()` clean up streams when a pipeline fails?

**Ideal answer**  
The stream docs say `stream.pipeline()` calls `stream.destroy(err)` on all streams except readable streams that already emitted `end` or `close` and writable streams that already emitted `finish` or `close`. They also warn that `pipeline()` can leave dangling listeners after the callback and may destroy an HTTP socket before an error response is sent.

**Generated answer**  
Based on the local Node.js knowledge base, the relevant API documentation is `stream`. The stream docs say `stream.pipeline()` calls `stream.destroy(err)` on the streams when the pipeline fails. The documented exceptions are readable streams that already emitted `end` or `close`, and writable streams that already emitted `finish` or `close`. The same docs also warn about dangling listeners after the callback. In `rfc: standardize stream.destroy() and pipe`, the cited text notes: Given that it is a de-facto standard, we can document it in the stream API, and add a default implementation of it. Use the cited docs as the source of truth.

**Retrieved citations**

- `stream`
  - source_type: `doc`
  - chunk_id: `doc-api-stream-md-stream-api-for-stream-consumers-stream-pipeline-streams-callback-146`
  - excerpt: `stream.pipeline()` will call `stream.destroy(err)` on all streams except: * `Readable` streams which have emitted `'end'` or `'close'`. * `Writable` streams which have emitted `'finish'` or `'close'`. `stream.pipeline()` leaves dangling event listeners on the streams after the `callback` has bee...
- `rfc: standardize stream.destroy() and pipe`
  - source_type: `resolved_issue`
  - chunk_id: `issue-4401-excluded-001`
  - excerpt: Given that it is a de-facto standard, we can document it in the stream API, and add a default implementation of it.

**Frozen judge result**

- answer_relevancy: `0.5193`
- faithfulness: `0.6000`
- citation_coverage: `True`
- groundedness_pass: `True`

**Current label fields**

- human_faithful: `True`
- human_relevant: `True`
- review_status: `human_spot_checked`
- human_notes: Second manual review after deterministic synthesis improvements: the answer now states that stream.pipeline() calls stream.destroy(err), includes the readable/writable end-or-close exceptions, and mentions the dangling-listener warning. This is now faithful and relevant.

**Checklist**

- [ ] Does the answer address the question?
- [ ] Is the answer supported by the citations?
- [ ] Does it avoid unsupported fixes or claims?
- [ ] Are the citations useful?
- [ ] Should this be marked `human_spot_checked`?

## rag-golden-002

**Question**  
Where do the Node.js DNS docs list resolver error codes such as `dns.NODATA` and `dns.TIMEOUT`?

**Ideal answer**  
The DNS docs have an Error codes section listing resolver failures such as `dns.NODATA`, `dns.FORMERR`, `dns.SERVFAIL`, `dns.NOTFOUND`, `dns.CONNREFUSED`, and `dns.TIMEOUT`.

**Generated answer**  
Based on the local Node.js knowledge base, the relevant API documentation is `dns`. The DNS > Error codes section lists resolver error codes including `dns.NODATA`, `dns.FORMERR`, `dns.SERVFAIL`, `dns.NOTFOUND`, `dns.CONNREFUSED`, `dns.TIMEOUT`. Use the cited docs as the source of truth.

**Retrieved citations**

- `errors`
  - source_type: `doc`
  - chunk_id: `doc-api-errors-md-errors-node-js-error-codes-err-dns-set-servers-failed-116`
  - excerpt: errors Errors > Node.js error codes > `ERR_DNS_SET_SERVERS_FAILED` `c-ares` failed to set the DNS server.
- `dns`
  - source_type: `doc`
  - chunk_id: `doc-api-dns-md-dns-error-codes-081`
  - excerpt: dns DNS > Error codes Each DNS query can return one of the following error codes: * `dns.NODATA`: DNS server returned an answer with no data. * `dns.FORMERR`: DNS server claims query was misformatted. * `dns.SERVFAIL`: DNS server returned general failure. * `dns.NOTFOUND`: Domain name not found....

**Frozen judge result**

- answer_relevancy: `0.5395`
- faithfulness: `0.4118`
- citation_coverage: `True`
- groundedness_pass: `False`

**Current label fields**

- human_faithful: `True`
- human_relevant: `True`
- review_status: `human_spot_checked`
- human_notes: Second manual review after deterministic synthesis improvements: the answer now points to the DNS > Error codes section and lists resolver codes including dns.NODATA and dns.TIMEOUT. This is now faithful and relevant.

**Checklist**

- [ ] Does the answer address the question?
- [ ] Is the answer supported by the citations?
- [ ] Does it avoid unsupported fixes or claims?
- [ ] Are the citations useful?
- [ ] Should this be marked `human_spot_checked`?

## rag-golden-014

**Question**  
What resolved Node.js issue reports a memory leak when `https.request()` hits `ECONNRESET`?

**Ideal answer**  
This issue reports that repeated `https.request()` calls against a host that resets the connection can drive process memory up to hundreds of megabytes and keep it there, even after manual garbage collection. The reporter included a small reproduction using two scripts and observed the leak on Node 6.8.0 and 7.0.0.

**Generated answer**  
Based on the local Node.js knowledge base, the closest resolved issue evidence is `Memory leak for https.request() on ECONNRESET`. I experience a memory leak when doing https requests to a host that resets the connection. The report says the memory usage doesn't change even when GC runs every second. 

**Retrieved citations**

- `Memory leak for https.request() on ECONNRESET`
  - source_type: `resolved_issue`
  - chunk_id: `issue-8827-test-001`
  - excerpt: I experience a memory leak when doing https requests to a host that resets the connection. The report says the memory usage doesn't change even when GC runs every second.
- `Response strings and closures objects leak with http.Agent enabled (Memory Leak)`
  - source_type: `resolved_issue`
  - chunk_id: `issue-9530-excluded-001`
  - excerpt: Response strings and closures objects leak with http.Agent enabled (Memory Leak) * **Version**: v6.9.1 * **Platform**: Linux ip-172-31-46-151 4.4.11-23.53.amzn1.x86_64 #1 SMP Wed Jun 1 22:22:50 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux * **Subsystem**: Http(s...
- `high tls memory usage (rss)`
  - source_type: `resolved_issue`
  - chunk_id: `issue-1522-excluded-001`
  - excerpt: high tls memory usage (rss) https.request leaks in this example: `rss` grows over time, `heapUsed` remains about constant (~30m).
- `Massive memory leak in HTTP 'upgrade' event`
  - source_type: `resolved_issue`
  - chunk_id: `issue-6632-excluded-001`
  - excerpt: Massive memory leak in HTTP 'upgrade' event - **Version**: 5.11.0 - **Platform**: Linux - **Subsystem**: HTTP I'm running this server: With my own benchmark that pretty much only sends a WebSocket upgrade request and then receives whatever the server sends back. Running this benchmark against thi...
- `socket hang up on https request`
  - source_type: `resolved_issue`
  - chunk_id: `issue-9845-excluded-001`
  - excerpt: socket hang up on https request * **Version**:v6.9.1 * **Platform**:Linux 4.4.0-47-generic #68-Ubuntu SMP x86_64 GNU/Linux * **Subsystem**:tls This code is giving me socket hang up error:

**Frozen judge result**

- answer_relevancy: `0.3060`
- faithfulness: `0.9130`
- citation_coverage: `True`
- groundedness_pass: `True`

**Current label fields**

- human_faithful: `True`
- human_relevant: `True`
- review_status: `human_spot_checked`
- human_notes: Second manual review after deterministic synthesis improvements: the answer still correctly identifies the https.request ECONNRESET memory-leak issue and now uses cleaner grounded symptom text. Keep faithful and relevant true.

**Checklist**

- [ ] Does the answer address the question?
- [ ] Is the answer supported by the citations?
- [ ] Does it avoid unsupported fixes or claims?
- [ ] Are the citations useful?
- [ ] Should this be marked `human_spot_checked`?

## rag-golden-018

**Question**  
What resolved issue describes `dns.lookup()` blocking other filesystem or serial I/O?

**Ideal answer**  
This issue says slow or failing DNS lookups can make `dns.lookup()` saturate the `libuv` threadpool because it relies on blocking `getaddrinfo` calls. The reporter observed that this delayed other work such as serial port and filesystem I/O.

**Generated answer**  
Based on the local Node.js knowledge base, the closest resolved issue evidence is `dns.lookup blocks filesystem I/O`. On networks with slow DNS response, or where DNS requests time out and fail, blocking calls to `getaddrinfo` issued by `dns.lookup` saturate Node's `libuv` threadpool and delay serialport or filesystem IO. 

**Retrieved citations**

- `dns.lookup blocks filesystem I/O`
  - source_type: `resolved_issue`
  - chunk_id: `issue-8436-test-001`
  - excerpt: On networks with slow DNS response, or where DNS requests time out and fail, blocking calls to `getaddrinfo` issued by `dns.lookup` saturate Node's `libuv` threadpool and delay serialport or filesystem IO.
- `Add version of dns.lookup that returns all results`
  - source_type: `resolved_issue`
  - chunk_id: `issue-736-excluded-001`
  - excerpt: Blocking calls to `getaddrinfo` issued by `dns.lookup` saturate Node's `libuv` threadpool and delay serialport or filesystem IO.
- `DNS lookup failure dns.js:82`
  - source_type: `resolved_issue`
  - chunk_id: `issue-4545-excluded-001`
  - excerpt: DNS lookup failure dns.js:82 here's the relevant line in node.js lib (https://github.com/nodejs/node/blob/master/lib/dns.js#L82) I have a bot running that polls an sftp server for the existence of a file that is uploaded daily.
- `dns`
  - source_type: `doc`
  - chunk_id: `doc-api-dns-md-dns-implementation-considerations-dns-lookup-083`
  - excerpt: dns DNS > Implementation considerations > `dns.lookup()` Under the hood, [`dns.lookup()`][] uses the same operating system facilities as most other programs. For instance, [`dns.lookup()`][] will almost always resolve a given name the same way as the `ping` command. On most POSIX-like operating s...

**Frozen judge result**

- answer_relevancy: `0.3483`
- faithfulness: `0.9167`
- citation_coverage: `True`
- groundedness_pass: `True`

**Current label fields**

- human_faithful: `True`
- human_relevant: `True`
- review_status: `human_spot_checked`
- human_notes: Second manual review after deterministic synthesis improvements: the answer still correctly connects dns.lookup to blocking getaddrinfo/libuv threadpool behavior and delayed serial/filesystem I/O. Keep faithful and relevant true.

**Checklist**

- [ ] Does the answer address the question?
- [ ] Is the answer supported by the citations?
- [ ] Does it avoid unsupported fixes or claims?
- [ ] Are the citations useful?
- [ ] Should this be marked `human_spot_checked`?

## rag-golden-021

**Question**  
What resolved issue asks whether `tls.createServer()` should document `secureOptions` for limiting TLS versions?

**Ideal answer**  
This issue says the reporter found `secureOptions` on `tls.createServer()` and expected it to be the way to restrict supported TLS versions, but could not find it documented. The question was whether the option should be documented or was intended for deprecation.

**Generated answer**  
Based on the local Node.js knowledge base, the closest resolved issue evidence is `tls.createServer secureOptions`. The issue says the reporter found `secureOptions` on `tls.createServer()` as a way to limit supported TLS versions and could not find it documented. It asks whether that option should be documented or was intended for deprecation/removal. 

**Retrieved citations**

- `tls.createServer secureOptions`
  - source_type: `resolved_issue`
  - chunk_id: `issue-9025-test-001`
  - excerpt: The issue says the reporter found `secureOptions` on `tls.createServer()` as a way to limit supported TLS versions and could not find it documented. It asks whether that option should be documented or was intended for deprecation/removal.
- `tls.TLSSocket does not emit error event on handshake failure`
  - source_type: `resolved_issue`
  - chunk_id: `issue-8803-excluded-001`
  - excerpt: tls.TLSSocket does not emit error event on handshake failure - **Version**: v6.5.0 - **Platform**: Linux 4.4.0-38-generic - **Subsystem**: TLS/SSL When upgrading `net.Socket` to `tls.TLSSocket`, if there is a handshake failure, no (documented) event is emit...
- `tls`
  - source_type: `doc`
  - chunk_id: `doc-api-tls-md-tls-ssl-tls-createsecurecontext-options-113`
  - excerpt: The possible values are listed as [SSL\_METHODS][SSL_METHODS], use the function names as strings. For example, use `'TLSv1_1_method'` to force TLS version 1.1, or `'TLS_method'` to allow any TLS protocol version up to TLSv1.3. It is not recommended to use TLS versions less than 1.2, but it may be...

**Frozen judge result**

- answer_relevancy: `0.7097`
- faithfulness: `0.9200`
- citation_coverage: `True`
- groundedness_pass: `True`

**Current label fields**

- human_faithful: `True`
- human_relevant: `True`
- review_status: `human_spot_checked`
- human_notes: Second manual review after deterministic synthesis improvements: the answer now clearly describes the tls.createServer secureOptions documentation/deprecate-or-remove question without leaking internal implementation text. This is now faithful and relevant.

**Checklist**

- [ ] Does the answer address the question?
- [ ] Is the answer supported by the citations?
- [ ] Does it avoid unsupported fixes or claims?
- [ ] Are the citations useful?
- [ ] Should this be marked `human_spot_checked`?

