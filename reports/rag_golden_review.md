# RAG Golden Candidate Review

## rag-golden-001

- Source type: `doc`
- Question: Which Node.js stream docs cover `stream.pipeline(streams, callback)`?
- Ideal answer: stream.pipeline() will call stream.destroy(err) on all streams except: * Readable streams which have emitted 'end' or 'close'. * Writable streams which have emitted 'finish' or 'close'.
- Ground truth chunk ids: `doc-api-stream-md-stream-api-for-stream-consumers-stream-pipeline-streams-callback-146`
- Source titles: stream

### Referenced chunks

#### doc-api-stream-md-stream-api-for-stream-consumers-stream-pipeline-streams-callback-146

```text
`stream.pipeline()` will call `stream.destroy(err)` on all streams except:
* `Readable` streams which have emitted `'end'` or `'close'`.
* `Writable` streams which have emitted `'finish'` or `'close'`. `stream.pipeline()` leaves dangling event listeners on the streams
after the `callback` has been invoked. In the case of reuse of streams after
failure, this can cause event listener leaks and swallowed errors. If the last
stream is readable, dangling event listeners will be removed so that the last
stream can be consumed later. `stream.pipeline()` closes all the streams when an error is raised. The `IncomingRequest` usage with `pipeline` could lead to an unexpected behavior
once it would destroy the socket without sending the expected response. See the example below:
```js
const fs = require('node:fs');
const http = require('node:http');
const { pipeline } = require('node:stream');
const server = http.createServer((req, res) => {
const fileStream = fs.createReadStream('./fileNotExist.txt');
pipeline(fileStream, res, (err) => {
if (err) {
console.log(err); // No such file
// this message can't be sent once `pipeline` already destroyed the socket
return res.end('error!!!');
}
});
});
```
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-002

- Source type: `doc`
- Question: Which Node.js dns docs cover Error codes?
- Ideal answer: Each DNS query can return one of the following error codes: * dns.NODATA: DNS server returned an answer with no data. * dns.FORMERR: DNS server claims query was misformatted.
- Ground truth chunk ids: `doc-api-dns-md-dns-error-codes-081`
- Source titles: dns

### Referenced chunks

#### doc-api-dns-md-dns-error-codes-081

```text
Document: dns
Section path: DNS > Error codes

Each DNS query can return one of the following error codes:
* `dns.NODATA`: DNS server returned an answer with no data.
* `dns.FORMERR`: DNS server claims query was misformatted.
* `dns.SERVFAIL`: DNS server returned general failure.
* `dns.NOTFOUND`: Domain name not found.
* `dns.NOTIMP`: DNS server does not implement the requested operation.
* `dns.REFUSED`: DNS server refused query.
* `dns.BADQUERY`: Misformatted DNS query.
* `dns.BADNAME`: Misformatted host name.
* `dns.BADFAMILY`: Unsupported address family.
* `dns.BADRESP`: Misformatted DNS reply.
* `dns.CONNREFUSED`: Could not contact DNS servers.
* `dns.TIMEOUT`: Timeout while contacting DNS servers.
* `dns.EOF`: End of file.
* `dns.FILE`: Error reading file.
* `dns.NOMEM`: Out of memory.
* `dns.DESTRUCTION`: Channel is being destroyed.
* `dns.BADSTR`: Misformatted string.
* `dns.BADFLAGS`: Illegal flags specified.
* `dns.NONAME`: Given host name is not numeric.
* `dns.BADHINTS`: Illegal hints flags specified.
* `dns.NOTINITIALIZED`: c-ares library initialization not yet performed.
* `dns.LOADIPHLPAPI`: Error loading `iphlpapi.dll`.
* `dns.ADDRGETNETWORKPARAMS`: Could not find `GetNetworkParams` function.
* `dns.CANCELLED`: DNS query cancelled.
The `dnsPromises` API also exports the above error codes, e.g., `dnsPromises.NODATA`.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-003

- Source type: `doc`
- Question: Which Node.js http docs cover `response.write(chunk[, encoding][, callback])`?
- Ideal answer: * chunk {string|Buffer|Uint8Array} * encoding {string} **Default:** 'utf8' * callback {Function} * Returns: {boolean} If this method is called and [response.writeHead()][] has not been called, it will switch to implicit header mode and flush the implicit headers. This sends a chu
- Ground truth chunk ids: `doc-api-http-md-http-class-http-serverresponse-response-write-chunk-encoding-callback-135`
- Source titles: http

### Referenced chunks

#### doc-api-http-md-http-class-http-serverresponse-response-write-chunk-encoding-callback-135

```text
* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string} **Default:** `'utf8'`
* `callback` {Function}
* Returns: {boolean}
If this method is called and [`response.writeHead()`][] has not been called,
it will switch to implicit header mode and flush the implicit headers. This sends a chunk of the response body. This method may
be called multiple times to provide successive parts of the body. If `rejectNonStandardBodyWrites` is set to true in `createServer`
then writing to the body is not allowed when the request method or response
status do not support content. If an attempt is made to write to the body for a
HEAD request or as part of a `204` or `304`response, a synchronous `Error`
with the code `ERR_HTTP_BODY_NOT_ALLOWED` is thrown. `chunk` can be a string or a buffer. If `chunk` is a string,
the second parameter specifies how to encode it into a byte stream. `callback` will be called when this chunk of data is flushed. This is the raw HTTP body and has nothing to do with higher-level multi-part
body encodings that may be used. The first time [`response.write()`][] is called, it will send the buffered
header information and the first chunk of the body to the client. The second
time [`response.write()`][] is called, Node.js assumes data will be streamed,
and sends the new data separately. That is, the response is buffered up to the
first chunk of the body.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-004

- Source type: `doc`
- Question: Where do the Node.js docs explain Integration with DevTools in inspector?
- Ideal answer: > Stability: 1.1 - Active development The node:inspector module provides an API for integrating with devtools that support Chrome DevTools Protocol. DevTools frontends connected to a running Node.js instance can capture protocol events emitted from the instance and display them a
- Ground truth chunk ids: `doc-api-inspector-md-inspector-integration-with-devtools-030`
- Source titles: inspector

### Referenced chunks

#### doc-api-inspector-md-inspector-integration-with-devtools-030

```text
Document: inspector
Section path: Inspector > Integration with DevTools

> Stability: 1.1 - Active development
The `node:inspector` module provides an API for integrating with devtools that support Chrome DevTools Protocol.
DevTools frontends connected to a running Node.js instance can capture protocol events emitted from the instance
and display them accordingly to facilitate debugging.
The following methods broadcast a protocol event to all connected frontends.
The `params` passed to the methods can be optional, depending on the protocol.
```js
// The `Network.requestWillBeSent` event will be fired.
inspector.Network.requestWillBeSent({
requestId: 'request-id-1',
timestamp: Date.now() / 1000,
wallTime: Date.now(),
request: {
url: 'https://nodejs.org/en',
method: 'GET',
},
});
```
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-005

- Source type: `doc`
- Question: Where do the Node.js docs explain `fs.readFile(path[, options], callback)` in fs?
- Ideal answer: ``mjs import { readFile } from 'node:fs'; // macOS, Linux, and Windows readFile(' ', (err, data) => { // => [Error: EISDIR: illegal operation on a directory, read ] }); // FreeBSD readFile(' ', (err, data) => { // => null, }); ` It is possible to abort an ongoing request using an
- Ground truth chunk ids: `doc-api-fs-md-file-system-callback-api-fs-readfile-path-options-callback-156`
- Source titles: fs

### Referenced chunks

#### doc-api-fs-md-file-system-callback-api-fs-readfile-path-options-callback-156

```text
```mjs
import { readFile } from 'node:fs';
// macOS, Linux, and Windows
readFile('<directory>', (err, data) => {
// => [Error: EISDIR: illegal operation on a directory, read <directory>]
});
//  FreeBSD
readFile('<directory>', (err, data) => {
// => null, <data>
});
```
It is possible to abort an ongoing request using an `AbortSignal`. If a
request is aborted the callback is called with an `AbortError`:
```mjs
import { readFile } from 'node:fs';
const controller = new AbortController();
const signal = controller.signal;
readFile(fileInfo[0].name, { signal }, (err, buf) => {
// ...
});
// When you want to abort the request
controller.abort();
```
The `fs.readFile()` function buffers the entire file. To minimize memory costs,
when possible prefer streaming via `fs.createReadStream()`. Aborting an ongoing request does not abort individual operating
system requests but rather the internal buffering `fs.readFile` performs.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-006

- Source type: `doc`
- Question: Which Node.js errors docs cover Common system errors?
- Ideal answer: This is a list of system errors commonly-encountered when writing a Node.js program. For a comprehensive list, see the [errno(3) man page][].
- Ground truth chunk ids: `doc-api-errors-md-errors-class-systemerror-common-system-errors-036`
- Source titles: errors

### Referenced chunks

#### doc-api-errors-md-errors-class-systemerror-common-system-errors-036

```text
This is a list of system errors commonly-encountered when writing a Node.js
program. For a comprehensive list, see the [`errno`(3) man page][].
* `EACCES` (Permission denied): An attempt was made to access a file in a way
forbidden by its file access permissions.
* `EADDRINUSE` (Address already in use): An attempt to bind a server
([`net`][], [`http`][], or [`https`][]) to a local address failed due to
another server on the local system already occupying that address.
* `ECONNREFUSED` (Connection refused): No connection could be made because the
target machine actively refused it. This usually results from trying to
connect to a service that is inactive on the foreign host.
* `ECONNRESET` (Connection reset by peer): A connection was forcibly closed by
a peer. This normally results from a loss of the connection on the remote
socket due to a timeout or reboot. Commonly encountered via the [`http`][]
and [`net`][] modules.
* `EEXIST` (File exists): An existing file was the target of an operation that
required that the target not exist.
* `EISDIR` (Is a directory): An operation expected a file, but the given
pathname was a directory.
* `EMFILE` (Too many open files in system): Maximum number of
[file descriptors][] allowable on the system has been reached, and
requests for another descriptor cannot be fulfilled until at least one
has been closed.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-007

- Source type: `doc`
- Question: Which Node.js http2 docs cover `response.write(chunk[, encoding][, callback])`?
- Ideal answer: * chunk {string|Buffer|Uint8Array} * encoding {string} * callback {Function} * Returns: {boolean} If this method is called and [response.writeHead()][] has not been called, it will switch to implicit header mode and flush the implicit headers. This sends a chunk of the response b
- Ground truth chunk ids: `doc-api-http2-md-http-2-compatibility-api-class-http2-http2serverresponse-response-write-chunk-encoding-callback-242`
- Source titles: http2

### Referenced chunks

#### doc-api-http2-md-http-2-compatibility-api-class-http2-http2serverresponse-response-write-chunk-encoding-callback-242

```text
* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string}
* `callback` {Function}
* Returns: {boolean}
If this method is called and [`response.writeHead()`][] has not been called,
it will switch to implicit header mode and flush the implicit headers. This sends a chunk of the response body. This method may
be called multiple times to provide successive parts of the body. In the `node:http` module, the response body is omitted when the
request is a HEAD request. Similarly, the `204` and `304` responses
_must not_ include a message body. `chunk` can be a string or a buffer. If `chunk` is a string,
the second parameter specifies how to encode it into a byte stream. By default the `encoding` is `'utf8'`. `callback` will be called when this chunk
of data is flushed. This is the raw HTTP body and has nothing to do with higher-level multi-part
body encodings that may be used. The first time [`response.write()`][] is called, it will send the buffered
header information and the first chunk of the body to the client. The second
time [`response.write()`][] is called, Node.js assumes data will be streamed,
and sends the new data separately. That is, the response is buffered up to the
first chunk of the body. Returns `true` if the entire data was flushed successfully to the kernel
buffer. Returns `false` if all or part of the data was queued in user memory.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-008

- Source type: `doc`
- Question: Where do the Node.js docs explain Session tickets in tls?
- Ideal answer: The servers encrypt the entire session state and send it to the client as a "ticket". When reconnecting, the state is sent to the server in the initial connection.
- Ground truth chunk ids: `doc-api-tls-md-tls-ssl-tls-ssl-concepts-session-resumption-session-tickets-018`
- Source titles: tls

### Referenced chunks

#### doc-api-tls-md-tls-ssl-tls-ssl-concepts-session-resumption-session-tickets-018

```text
The servers encrypt the entire session state and send it
to the client as a "ticket". When reconnecting, the state is sent to the server
in the initial connection. This mechanism avoids the need for a server-side
session cache. If the server doesn't use the ticket, for any reason (failure
to decrypt it, it's too old, etc.), it will create a new session and send a new
ticket. See [RFC 5077][] for more information. Resumption using session tickets is becoming commonly supported by many web
browsers when making HTTPS requests. For Node.js, clients use the same APIs for resumption with session identifiers
as for resumption with session tickets. For debugging, if
[`tls.TLSSocket.getTLSTicket()`][] returns a value, the session data contains a
ticket, otherwise it contains client-side session state. With TLSv1.3, be aware that multiple tickets may be sent by the server,
resulting in multiple `'session'` events, see [`'session'`][] for more
information. Single process servers need no specific implementation to use session tickets. To use session tickets across server restarts or load balancers, servers must
all have the same ticket keys. There are three 16-byte keys internally, but the
tls API exposes them as a single 48-byte buffer for convenience.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-009

- Source type: `doc`
- Question: Which Node.js https docs cover `https.request(url[, options][, callback])`?
- Ideal answer: ``js const options = { hostname: 'encrypted.google.com', port: 443, path: '/', method: 'GET', key: fs.readFileSync('private-key.pem'), cert: fs.readFileSync('certificate.pem'), agent: false, }; const req = https.request(options, (res) => { // ... }); ` Example using a [URL][] as
- Ground truth chunk ids: `doc-api-https-md-https-https-request-url-options-callback-026`
- Source titles: https

### Referenced chunks

#### doc-api-https-md-https-https-request-url-options-callback-026

```text
```js
const options = {
hostname: 'encrypted.google.com',
port: 443,
path: '/',
method: 'GET',
key: fs.readFileSync('private-key.pem'),
cert: fs.readFileSync('certificate.pem'),
agent: false,
};
const req = https.request(options, (res) => {
// ...
});
```
Example using a [`URL`][] as `options`:
```js
const options = new URL('https://abc:xyz@example.com');
const req = https.request(options, (res) => {
// ...
});
```
Example pinning on certificate fingerprint, or the public key (similar to
`pin-sha256`):
```mjs
import { checkServerIdentity } from 'node:tls';
import { Agent, request } from 'node:https';
import { createHash } from 'node:crypto';
function sha256(s) {
return createHash('sha256').update(s).digest('base64');
}
const options = {
hostname: 'github.com',
port: 443,
path: '/',
method: 'GET',
checkServerIdentity: function(host, cert) {
// Make sure the certificate is issued to the host we are connected to
const err = checkServerIdentity(host, cert);
if (err) {
return err;
}
// Pin the public key, similar to HPKP pin-sha256 pinning
const pubkey256 = 'SIXvRyDmBJSgatgTQRGbInBaAK+hZOQ18UmrSwnDlK8=';
if (sha256(cert.pubkey) !== pubkey256) {
const msg = 'Certificate verification error: ' +
`The public key of '${cert.subject.CN}' ` +
'does not match our pinned fingerprint';
return new Error(msg);
}
// Pin the exact certificate, rather than the pub key
const cert256 = 'FD:6E:9B:0E:
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-010

- Source type: `doc`
- Question: Which Node.js zlib docs cover Compressing HTTP requests and responses?
- Ideal answer: ; } else if (/\bzstd\b/.test(acceptEncoding)) { response.writeHead(200, { 'Content-Encoding': 'zstd' }); pipeline(raw, zlib.createZstdCompress(), response, onError); } else { response.writeHead(200, {}); pipeline(raw, response, onError); } }).listen(1337); `` ``cjs // server exam
- Ground truth chunk ids: `doc-api-zlib-md-zlib-compressing-http-requests-and-responses-012`
- Source titles: zlib

### Referenced chunks

#### doc-api-zlib-md-zlib-compressing-http-requests-and-responses-012

```text
;
} else if (/\bzstd\b/.test(acceptEncoding)) {
response.writeHead(200, { 'Content-Encoding': 'zstd' });
pipeline(raw, zlib.createZstdCompress(), response, onError);
} else {
response.writeHead(200, {});
pipeline(raw, response, onError);
}
}).listen(1337);
```
```cjs
// server example
// Running a gzip operation on every request is quite expensive.
// It would be much more efficient to cache the compressed buffer.
const zlib = require('node:zlib');
const http = require('node:http');
const fs = require('node:fs');
const { pipeline } = require('node:stream');
http.createServer((request, response) => {
const raw = fs.createReadStream('index.html');
// Store both a compressed and an uncompressed version of the resource.
response.setHeader('Vary', 'Accept-Encoding');
const acceptEncoding = request.headers['accept-encoding'] || '';
const onError = (err) => {
if (err) {
// If an error occurs, there's not much we can do because
// the server has already sent the 200 response code and
// some amount of data has already been sent to the client.
// The best we can do is terminate the response immediately
// and log the error.
response.end();
console.error('An error occurred:', err);
}
};
// Note: This is not a conformant accept-encoding parser.
// See https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3
if (/\bdeflate\b/.test(acceptEncoding)) {
response.writeHead(200, { 'Conten
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-011

- Source type: `doc`
- Question: Where do the Node.js docs explain Permission Model constraints in permissions?
- Ideal answer: There are constraints you need to know before using this system: * The model does not inherit to a worker thread. * When using the Permission Model the following features will be restricted: * Native modules * Network * Child process * Worker Threads * Inspector protocol * File s
- Ground truth chunk ids: `doc-api-permissions-md-permissions-process-based-permissions-permission-model-permission-model-constraints-011`
- Source titles: permissions

### Referenced chunks

#### doc-api-permissions-md-permissions-process-based-permissions-permission-model-permission-model-constraints-011

```text
Document: permissions
Section path: Permissions > Process-based permissions > Permission Model > Permission Model constraints

There are constraints you need to know before using this system:
* The model does not inherit to a worker thread.
* When using the Permission Model the following features will be restricted:
* Native modules
* Network
* Child process
* Worker Threads
* Inspector protocol
* File system access
* WASI
* FFI
* The Permission Model is initialized after the Node.js environment is set up.
However, certain flags such as `--env-file` or `--openssl-config` are designed
to read files before environment initialization. As a result, such flags are
not subject to the rules of the Permission Model. The same applies for V8
flags that can be set via runtime through `v8.setFlagsFromString`.
* OpenSSL engines cannot be requested at runtime when the Permission
Model is enabled, affecting the built-in crypto, https, and tls modules.
* Run-Time Loadable Extensions cannot be loaded when the Permission Model is
enabled, affecting the sqlite module.
* Using existing file descriptors via the `node:fs` module bypasses the
Permission Model.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-012

- Source type: `doc`
- Question: Where do the Node.js docs explain Index in index?
- Ideal answer: * About this documentation * Usage and example * Assertion testing * Asynchronous context tracking * Async hooks * Buffer * C++ addons * C/C++ addons with Node-API * C++ embedder API * Child processes * Cluster * Command-line options * Console * Crypto * Debugger * Deprecated API
- Ground truth chunk ids: `doc-api-index-md-index-002`
- Source titles: index

### Referenced chunks

#### doc-api-index-md-index-002

```text
* [About this documentation](documentation.md)
* [Usage and example](synopsis.md)
<hr class="line"/>
* [Assertion testing](assert.md)
* [Asynchronous context tracking](async_context.md)
* [Async hooks](async_hooks.md)
* [Buffer](buffer.md)
* [C++ addons](addons.md)
* [C/C++ addons with Node-API](n-api.md)
* [C++ embedder API](embedding.md)
* [Child processes](child_process.md)
* [Cluster](cluster.md)
* [Command-line options](cli.md)
* [Console](console.md)
* [Crypto](crypto.md)
* [Debugger](debugger.md)
* [Deprecated APIs](deprecations.md)
* [Diagnostics Channel](diagnostics_channel.md)
* [DNS](dns.md)
* [Domain](domain.md)
* [Environment Variables](environment_variables.md)
* [Errors](errors.md)
* [Events](events.md)
* [File system](fs.md)
* [FFI](ffi.md)
* [Globals](globals.md)
* [HTTP](http.md)
* [HTTP/2](http2.md)
* [HTTPS](https.md)
* [Inspector](inspector.md)
* [Internationalization](intl.md)
* [Iterable Streams API](stream_iter.md)
* [Modules: CommonJS modules](modules.md)
* [Modules: ECMAScript modules](esm.md)
* [Modules: `node:module` API](module.md)
* [Modules: Packages](packages.md)
* [Modules: TypeScript](typescript.md)
* [Net](net.md)
* [OS](os.md)
* [Path](path.md)
* [Performance hooks](perf_hooks.md)
* [Permissions](permissions.md)
* [Process](process.md)
* [Punycode](punycode.md)
* [Query strings](querystring.md)
* [Readline](readline.md)
* [REPL](repl.md)
* [R
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-013

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses ECONNRESET problem with http.Server and https.Server (node 6.3, 6.2.2 and poss earlier)?
- Ideal answer: Problem: Node: 6.3 (and I believe all 6.x) AWS instance (zone us-west-2) - t2.small, m4.large - Centos 7 receiving the following error: Error: read ECONNRESET at exports._errnoException (util.js:1008:11) at TCP.onread (net.js:563:26) Similar results with different instance varian
- Ground truth chunk ids: `issue-7776-val-001`
- Source titles: ECONNRESET problem with http.Server and https.Server (node 6.3, 6.2.2 and poss earlier)

### Referenced chunks

#### issue-7776-val-001

```text
Issue: ECONNRESET problem with http.Server and https.Server (node 6.3, 6.2.2 and poss earlier)

Problem:
Node: 6.3 (and I believe all 6.x)
AWS instance (zone us-west-2) - t2.small, m4.large - Centos 7

receiving the following error:
Error: read ECONNRESET
      at exports._errnoException (util.js:1008:11)
      at TCP.onread (net.js:563:26)

Similar results with different instance variants, with different loads (from extremely light to extremely heavy).

I believe these may be idle sockets, and therefore the error should be handled by node.

The errors come through on both http and https (tls).   They can be trapped in http using .on('clientError'), or on https/tls using 'clientError' and 'tlsClientError' (comes through on both variants).

It's unclear how a user application can safely recover (so am process.exit()'ing for now - about twice a minute :(.

For context: here is the code from the node net.js module: (see my annotation re: line 563 of the code below)....... I haven't traced this back through libuv.

Thanks!

Peter B.

// if we didn't get any bytes, that doesn't necessarily mean EOF.
  // wait for the next one.
  if (nread === 0) {
    debug('not any data, keep waiting');
    return;
}
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-014

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses TODO/XXX/FIXME comments in lib directory?
- Ideal answer: // count the one we are adding, as well. // TODO(isaacs) clean this up state.pendingcb++; state.lastBufferedRequest = null; `` lib/_tls_common.js: ` c.infoAccess = {}; // XXX: More key validation?.
- Ground truth chunk ids: `issue-4642-excluded-003`
- Source titles: TODO/XXX/FIXME comments in lib directory

### Referenced chunks

#### issue-4642-excluded-003

```text
```
function writeAfterEnd(stream, cb) {
  var er = new Error('write after end');
  // TODO: defer error events consistently everywhere, not just the cb
  stream.emit('error', er);
  process.nextTick(cb, er);
...

// count the one we are adding, as well.
    // TODO(isaacs) clean this up
    state.pendingcb++;
    state.lastBufferedRequest = null;
```

lib/_tls_common.js:

```
    c.infoAccess = {};

// XXX: More key validation?
    info.replace(/([^\n:]*):([^\n]*)(?:\n|$)/g, function(all, key, val) {
      if (key === '__proto__')
```

lib/_tls_legacy.js:

```
  // side.
  //
  // TODO(indutny): Remove magic number, use watermark based limits
  if (!this._resumingSession &&
      this._opposite._internallyPendingBytes() < 128 * 1024) {
...

CryptoStream.prototype._read = function read(size) {
  // XXX: EOF?!
  if (!this.pair.ssl) return this.push(null);
```

lib/_tls_wrap.js:

```
      return cb(new Error('Socket is closed'));

// TODO(indutny): eventually disallow raw `SecureContext`
    if (context)
      self._handle.sni_context = context.context || context;
...
  // lib/net.js expect this value to be non-zero if write hasn't been flushed
  // immediately
  // TODO(indutny): rewise this solution, it might be 1 before handshake and
  // represent real writeQueueSize during regular writes.
  ssl.writeQueueSize = 1;
...
};

// TODO: support anonymous (nocert) and PSK
```
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-015

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses Stream stops reading from kernel halfway through in http.IncomingMessage?
- Ideal answer: Problem: - **Version**: v0.10.36 - **Platform**: Linux hd1app1 3.13.0-83-generic #127-Ubuntu SMP Fri Mar 11 00:25:37 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux - **Subsystem**: net.js, http.js, _stream_readable.js We've been investigating a memory leak issue where we have sockets th
- Ground truth chunk ids: `issue-7910-excluded-001`
- Source titles: Stream stops reading from kernel halfway through in http.IncomingMessage

### Referenced chunks

#### issue-7910-excluded-001

```text
Issue: Stream stops reading from kernel halfway through in http.IncomingMessage

Problem:
- **Version**:
  v0.10.36
- **Platform**:
  Linux hd1app1 3.13.0-83-generic #127-Ubuntu SMP Fri Mar 11 00:25:37 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux
- **Subsystem**:
  net.js, http.js, _stream_readable.js

We've been investigating a memory leak issue where we have sockets that remain stuck in `CLOSE_WAIT`. The sockets are being using to pull blob files (~ 250KB - 1MB in size) from Amazon S3. The code we use to pull the data is using the Knox library [https://github.com/Automattic/knox], but it's really just a wrapper around http.ClientRequest.
The code is straightforward and essentially boils down to:

```
var req = https.request(options);
req.end();
req.on('response', function (read_stream) {
  read_stream.on('data', function (chunk) {
    // buffer data
  }
  read_stream.on('end', function () {
    // call our main callback with buffered data
  }
```

I cannot reproduce this issue locally, but in production I'll have sockets stuck in this state even 10 minutes after a restart. Also, what I thought was just a memory leak appears to result in us silently not completing client request for the s3 data.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-016

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses Using the http module under certain network settings blocks fs?
- Ideal answer: Problem: - **Version**: 0.12.13, 4.0, 5.0 - **Platform**: Mac OSX El Capitan, Ubuntu 14.04 - **Subsystem**: The http core module blocks file IO under certain network settings. I can reproduce this 100% of the time on multiple Node versions and different operating systems.
- Ground truth chunk ids: `issue-7301-excluded-001`
- Source titles: Using the http module under certain network settings blocks fs

### Referenced chunks

#### issue-7301-excluded-001

```text
Issue: Using the http module under certain network settings blocks fs

Problem:
- **Version**: 0.12.13, 4.0, 5.0
- **Platform**: Mac OSX El Capitan, Ubuntu 14.04
- **Subsystem**:

The `http` core module blocks file IO under certain network settings.  I can reproduce this 100% of the time on multiple Node versions and different operating systems.

_Network settings:_
1. Connect your computer to wifi, then unplug the internet ethernet cable from the router.  
2. Do `ifconfig` on your computer, your should still have an ip address for wlan0 even though you don't have internet.

_Code sample:_

```
var path = require('path');
var http = require('http');
var fs = require('fs');
var stream = fs.createWriteStream(path.join(__dirname, 'testfile'));

setInterval(function(){
    //do http request
    http.get("http://httpbin.org/get", function(res) {
        console.log("Got response: " + res.statusCode);
    }).on('error', function(e) {
        console.log("Got error: " + e.message);
    });

    //write to file
    stream.write('aaa\n')
}, 1000);
```

If you run the code above under the setting I described, and tail `testfile`, then you should see 3 `aaa` before it stops writing to that file.

Resolution note:
Resolved issue corpus currently uses issue title/body only until comments are fetched.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-017

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses tls support requires dots at the end of the Alternative Subject Names?
- Ideal answer: Problem: Version: v6.2.0 Platform: Linux kanga 4.6.0-1-amd64 #1 SMP Debian 4.6.4-1 (2016-07-18) x86_64 GNU/Linux Subsystem: /lib/tls.js Its complaining that my host names in my self signed certificate don't end in a dot. I have never seen certificate examples where the names end
- Ground truth chunk ids: `issue-8008-excluded-001`
- Source titles: tls support requires dots at the end of the Alternative Subject Names

### Referenced chunks

#### issue-8008-excluded-001

```text
Issue: tls support requires dots at the end of the Alternative Subject Names

Problem:
Version: v6.2.0
Platform: Linux kanga 4.6.0-1-amd64 #1 SMP Debian 4.6.4-1 (2016-07-18) x86_64 GNU/Linux
Subsystem: /lib/tls.js

Its complaining that my host names in my self signed certificate don't end in a dot.  I have never seen certificate examples where the names end in dot.

```
Error: Hostname/IP doesn't match certificate's altnames: "Host: pas.accuvsion.dev. is not in the cert's altnames: DNS:pas.accuvision.local, DNS:pas.accuvision.dev, DNS:pas.rab, DNS:pas.home, DNS:pas.dev"
    at Object.checkServerIdentity (tls.js:203:15)
    at TLSSocket.<anonymous> (_tls_wrap.js:1061:29)
    at emitNone (events.js:86:13)
    at TLSSocket.emit (events.js:185:7)
    at TLSSocket._finishInit (_tls_wrap.js:580:8)
    at TLSWrap.ssl.onhandshakedone (_tls_wrap.js:412:38)
```

I am using the http2 module to make a request to my http2 web server.  Both are running in the same project.

I am using http2.request(options, callback) and with `options.hostname: 'pas.accuvision.dev'` as part of my options.  Using node-debug I can see it creating an array of DNS names (all without a dot at the end) and attempt to compare it with my hostname with a "." appended.  Needless to say it never matches and throws this error.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-018

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses make test fails with header_guard error in cpplint?
- Ideal answer: make directory /home/bujak_e/compile/node-v0.12.7' make cpplint make directory /home/bujak_e/compile/node-v0.12.7' Done processing src/async-wrap.cc Done processing src/cares_wrap.cc Done processing src/fs_event_wrap.cc Done processing src/handle_wrap.cc Done processing src/node_
- Ground truth chunk ids: `issue-2693-excluded-003`
- Source titles: make test fails with header_guard error in cpplint

### Referenced chunks

#### issue-2693-excluded-003

```text
50 files checked, no errors found.
make[1]: Leaving directory `/home/bujak_e/compile/node-v0.12.7'
make cpplint
make[1]: Entering directory `/home/bujak_e/compile/node-v0.12.7'
Done processing src/async-wrap.cc
Done processing src/cares_wrap.cc
Done processing src/fs_event_wrap.cc
Done processing src/handle_wrap.cc
Done processing src/node_buffer.cc
Done processing src/node.cc
Done processing src/node_constants.cc
Done processing src/node_contextify.cc
Done processing src/node_counters.cc
Done processing src/node_crypto_bio.cc
Done processing src/node_crypto.cc
Done processing src/node_crypto_clienthello.cc
Done processing src/node_dtrace.cc
Done processing src/node_file.cc
Done processing src/node_http_parser.cc
Done processing src/node_i18n.cc
Done processing src/node_javascript.cc
Done processing src/node_main.cc
Done processing src/node_os.cc
Done processing src/node_stat_watcher.cc
Done processing src/node_v8.cc
Done processing src/node_watchdog.cc
Done processing src/node_win32_etw_provider.cc
Done processing src/node_zlib.cc
Done processing src/pipe_wrap.cc
Done processing src/process_wrap.cc
Done processing src/signal_wrap.cc
Done processing src/smalloc.cc
Done processing src/spawn_sync.cc
Done processing src/stream_wrap.cc
Done processing src/string_bytes.cc
Done processing src/tcp_wrap.cc
Done processing src/timer_wrap.cc
Done processing src/tls_wrap.cc
Done processin
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-019

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses 278 tests failing under Ubuntu 14.04?
- Ideal answer: Error: listen EADDRINUSE :::12646 at Object.exports._errnoException (util.js:837:11) at exports._exceptionWithHostPort (util.js:860:20) at Server._listen2 (net.js:1231:14) at listen (net.js:1267:10) at Server.listen (net.js:1363:5) at Object. (/home/cschwenz/node/test/parallel/te
- Ground truth chunk ids: `issue-2969-excluded-045`
- Source titles: 278 tests failing under Ubuntu 14.04

### Referenced chunks

#### issue-2969-excluded-045

```text
Error: listen EADDRINUSE :::12646
    at Object.exports._errnoException (util.js:837:11)
    at exports._exceptionWithHostPort (util.js:860:20)
    at Server._listen2 (net.js:1231:14)
    at listen (net.js:1267:10)
    at Server.listen (net.js:1363:5)
    at Object.<anonymous> (/home/cschwenz/node/test/parallel/test-https-agent-servername.js:26:8)
    at Module._compile (module.js:434:26)
    at Object.Module._extensions..js (module.js:452:10)
    at Module.load (module.js:355:32)
    at Function.Module._load (module.js:310:12)
Command: out/Release/node /home/cschwenz/node/test/parallel/test-https-agent-servername.js
=== release test-https-agent ===                                 
Path: parallel/test-https-agent
getaddrinfo ENOTFOUND localhost localhost:12546
assert.js:89
  throw new assert.AssertionError({
  ^
AssertionError: 100 == 0
    at process.<anonymous> (/home/cschwenz/node/test/parallel/test-https-agent.js:52:10)
    at emitOne (events.js:82:20)
    at process.emit (events.js:169:7)
    at process.exit (node.js:737:17)
    at ClientRequest.<anonymous> (/home/cschwenz/node/test/parallel/test-https-agent.js:43:19)
    at emitOne (events.js:77:13)
    at ClientRequest.emit (events.js:169:7)
    at TLSSocket.socketErrorListener (_http_client.js:259:9)
    at emitOne (events.js:77:13)
    at TLSSocket.emit (events.js:169:7)
Command: out/Release/node /home/cschwenz/node/te
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-020

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses Planning for v6?
- Ideal answer: com/nodejs/node/pull/5382 - [7c48cb5601] - (SEMVER-MAJOR) crypto: Improve control of FIPS mode (Stefan Budeanu) https://github.com/nodejs/node/pull/5181 - [a1163582c5] - (SEMVER-MAJOR) crypto: pbkdf2 deprecate digest overload. (Tom Gallacher) https://github.com/nodejs/node/pull/4
- Ground truth chunk ids: `issue-5766-excluded-003`
- Source titles: Planning for v6

### Referenced chunks

#### issue-5766-excluded-003

```text
com/nodejs/node/pull/5382
- [7c48cb5601] - (SEMVER-MAJOR) crypto: Improve control of FIPS mode (Stefan Budeanu) https://github.com/nodejs/node/pull/5181
- [a1163582c5] - (SEMVER-MAJOR) crypto: pbkdf2 deprecate digest overload. (Tom Gallacher) https://github.com/nodejs/node/pull/4047
- [b010c87164] - (SEMVER-MAJOR) crypto, string_bytes: treat `buffer` str as `utf8` (Fedor Indutny) https://github.com/nodejs/node/pull/5522
- [dbdbdd4998] - (SEMVER-MAJOR) dns: add resolvePtr to query plain DNS PTR records (Daniel Turing) https://github.com/nodejs/node/pull/4921
- [c4ab861a49] - (SEMVER-MAJOR) dns: add failure test for dns.resolveXXX (Daniel Turing) https://github.com/nodejs/node/pull/4921
- [f3be421c1c] - (SEMVER-MAJOR) dns: coerce port to number in lookupService (Evan Lucas) https://github.com/nodejs/node/pull/4883
- [d8290286b3] - (SEMVER-MAJOR) doc: document deprecation of util._extend (Benjamin Gruenbaum) https://github.com/nodejs/node/pull/4903
- [90204cc468] - (SEMVER-MAJOR) domains: clear stack when no error handler (Julien Gilli) https://github.com/nodejs/node/pull/4659
- [8bb60e3c8d] - (SEMVER-MAJOR) fs: improve error message for invalid flag (James M Snell) https://github.com/nodejs/node/pull/5590
- [1d79787e2e] - (SEMVER-MAJOR) fs: add a temporary fix for re-evaluation support (Сковорода Никита Андреевич) https://github.com/nodejs/node/pull/5102
- [1124de2d76] - (SEMVER-
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-021

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses windows npm install errors?
- Ideal answer: Trace at TLSSocket.addListener (events.js:239:17) at TLSSocket.Readable.on (_stream_readable.js:680:33) at Request. (C:\Users\ahmed\AppData\Roaming\npm\node_modules\npm\node_modules\npm-registry-client\lib\request.js:153:7) at emitOne (events.js:77:13) at Request.emit (events.js:
- Ground truth chunk ids: `issue-8664-excluded-017`
- Source titles: windows npm install errors

### Referenced chunks

#### issue-8664-excluded-017

```text
Trace
    at TLSSocket.addListener (events.js:239:17)
    at TLSSocket.Readable.on (_stream_readable.js:680:33)
    at Request.<anonymous> (C:\Users\ahmed\AppData\Roaming\npm\node_modules\npm\node_modules\npm-registry-client\lib\request.js:153:7)
    at emitOne (events.js:77:13)
    at Request.emit (events.js:169:7)
    at ClientRequest.<anonymous> (C:\Users\ahmed\AppData\Roaming\npm\node_modules\npm\node_modules\request\request.js:791:10)
    at emitOne (events.js:82:20)
    at ClientRequest.emit (events.js:169:7)
    at tickOnSocket (_http_client.js:523:7)
    at onSocketNT (_http_client.js:535:5)
npm WARN deprecated minimatch@2.0.10: Please update to minimatch 3.0.2 or higher to avoid a RegExp DoS issue
npm WARN deprecated minimatch@0.2.14: Please update to minimatch 3.0.2 or higher to avoid a RegExp DoS issue
npm WARN deprecated lodash@1.0.2: lodash@<3.0.0 is no longer maintained. Upgrade to lodash@^4.0.0.
npm WARN deprecated graceful-fs@1.2.3: graceful-fs v3.0.0 and before will fail on node releases >= v7.0. Please update to graceful-fs@^4.0.0 as soon as possible. Use 'npm ls graceful-fs' to find it in the tree.
(node) warning: possible EventEmitter memory leak detected. 11 error listeners added. Use emitter.setMaxListeners() to increase limit.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-022

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses Node.js Foundation Core Technical Committee (CTC) Meeting 2016-08-10?
- Ideal answer: Extracted from **ctc-agenda** labelled issues and pull requests from the **nodejs org** prior to the meeting. ### nodejs/node - v4.5.0 proposal #7688 - buffer: hard-deprecate Buffer constructor #7152 - Revert "fs: add a temporary fix for re-evaluation support" #6413 - errors: add
- Ground truth chunk ids: `issue-8030-excluded-002`
- Source titles: Node.js Foundation Core Technical Committee (CTC) Meeting 2016-08-10

### Referenced chunks

#### issue-8030-excluded-002

```text
Extracted from **ctc-agenda** labelled issues and pull requests from the **nodejs org** prior to the meeting.
### nodejs/node
- v4.5.0 proposal [#7688](https://github.com/nodejs/node/pull/7688)
- buffer: hard-deprecate Buffer constructor [#7152](https://github.com/nodejs/node/pull/7152)
- Revert "fs: add a temporary fix for re-evaluation support" [#6413](https://github.com/nodejs/node/pull/6413)
- errors: add internal/errors module [#6573](https://github.com/nodejs/node/pull/6573)
- Introduce staging branch for stable release streams [#6306](https://github.com/nodejs/node/issues/6306)
### nodejs/node-eps
- proposal: WHATWG URL standard implementation [#28](https://github.com/nodejs/node-eps/pull/28)
- discussion: modules interop overhaul (https://gist.github.com/bmeck/52ee45e7c34d1eac44ce8c5fe436d753)
## Invited
- Anna Henningsen @addaleax (CTC)
- Bradley Meck @bmeck (observer/GoDaddy/TC39)
- Ben Noordhuis @bnoordhuis (CTC)
- Сковорода Никита Андреевич @ChALkeR (CTC)
- Chris Dickinson @chrisdickinson (CTC)
- Colin Ihrig @cjihrig (CTC)
- Evan Lucas @evanlucas (CTC)
- Jeremiah Senkpiel @Fishrock123 (CTC)
- Tracy Hinds @hackygolucky (observer/Node.js Foundation)
- Fedor Indutny @indutny (CTC)
- James M Snell @jasnell (CTC)
- Josh Gavant @joshgav (observer/Microsoft)
- Michael Dawson @mhdawson (CTC)
- Julien Gilli @misterdjules (CTC)
- Mikeal Rogers @mikeal (observer/Node.js Founda
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-023

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses crypto: Resolve FIPS test failures and API issues?
- Ideal answer: Problem: # Issue Overview The issue of FIPS-compliant encryption in Node.js has been brought up before and support for compiling with FIPS-compliant OpenSSL was added. The FIPS build instructions have recently been modified to insure compliance with FIPS 140-2 requirements.
- Ground truth chunk ids: `issue-3760-excluded-001`
- Source titles: crypto: Resolve FIPS test failures and API issues

### Referenced chunks

#### issue-3760-excluded-001

```text
Issue: crypto: Resolve FIPS test failures and API issues

Problem:
# Issue Overview

The issue of FIPS-compliant encryption in Node.js has been brought up [before](https://github.com/nodejs/node-v0.x-archive/issues/25463)  and support for compiling with FIPS-compliant OpenSSL was [added](https://github.com/nodejs/node/pull/1890). The FIPS build instructions have recently been [modified](https://github.com/nodejs/node/issues/2242) to insure compliance with FIPS 140-2 requirements.

However, running the Node.js test suite (“tools/test.py --verbose”) with the FIPS-compliant OpenSSL crypto module produces a large number of test failures. These failures are a  significant roadblock to adoption of Node.js in real life applications requiring FIPS compliance, because it is unclear to prospective users if Node.js can actually work correctly in this mode.

I have spent some time debugging the test failures and have produced a series of pull requests to address them. These pull requests are split up under several “themes” below.
# Pull Requests
## Documentation Update

https://github.com/nodejs/node/pull/3752 (Landed)
## Error Checking

https://github.com/nodejs/node/pull/3753 (Landed)
## FIPS-incompatible API

https://github.com/nodejs/node/pull/3754 (Landed)
## TLS Wrap

https://github.com/nodejs/node/pull/3755 (Landed)
## OpenSSL Known Bug Workaround
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-024

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses docs do not state at what version an API was introduced (or deprecated)?
- Ideal answer: Documentation files for which this is definitely worthwhile: - [x] assert.md – @Trott in f52b2f116bf510e2af8750061ac6f8a0c9caa653 (#6688) - [x] buffer.md – @addaleax in 4dcc692cada019cd2661ff807d829493ebf71594 (#6495) - [x] child_process.md – @addaleax in 27d2267066add18a1eafa2ac
- Ground truth chunk ids: `issue-6578-excluded-002`
- Source titles: docs do not state at what version an API was introduced (or deprecated)

### Referenced chunks

#### issue-6578-excluded-002

```text
Documentation files for which this is definitely worthwhile:
- [x] assert.md – @Trott in f52b2f116bf510e2af8750061ac6f8a0c9caa653 (#6688)
- [x] buffer.md – @addaleax in 4dcc692cada019cd2661ff807d829493ebf71594 (#6495)
- [x] child_process.md – @addaleax in 27d2267066add18a1eafa2ac852ffdb4ae3198be (#6927)
- [x] cli.md – @Trott in 90675818eede96a063489109f86022dd13ad75cb (#6960)
- [x] cluster.md – @addaleax in c628982a06e479f0d7d943c13131108924873ba4 (#7640)
- [x] console.md – @edsadr in 51b8a79bd46a28c2f576a579f258c2222e1a951b (#6995) 
- [x] crypto.md – @lpinca in cfe8278328d190279532ab9b7fd13ae1bfd78ee2 (#8281)
- [x] dgram.md – @lpinca in 379d9162a2d992f7ff8a20d00f088ede1bf2f0fe (#8196)
- [x] dns.md – @julianduque in 71996506e9a979e73d20bd418a5c7e34a92c3f08 (#7021)
- [x] events.md – @lpinca in 769f63ccd8437045af5ddf1f418c53d2319597ed (#7822)
- [x] fs.md – @addaleax in ba10ea8f3af4a1af5c2f7df3e4f5af348f09e97b (#6717)
- [x] http.md – @addaleax in 72500f942b85e7fe66176b2807663aa225015e39 (#7392)
- [x] https.md – @addaleax in e8356b25cdf43079e8a6d74e02df67a49f64e471 (#7392)
- [x] modules.md – @lpinca in df4880de557fabafb625745c6ea75d3b755595d2 (#8250)
- [x] net.md – @italoacasas in 8bccc9e6c82c558132a28a462e9dd573ae0302c6 (#7038)
- [x] os.md – @bengl in 5a8c66a252c16b0d181fd7f1b3232941e5644971 (#6609)
- [x] path.md – @julianduque in bed44c94a0f05748fc5160610db33ed15f1f540c (#6985)
-
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?

## rag-golden-025

- Source type: `resolved_issue`
- Question: What resolved Node.js issue discusses node@0.10 -> iojs@1.0.0 changelog?
- Ideal answer: Problem: TC meeting today decided it would be good to have at least a broad-strokes changes document to show what's different in this release but we have to divide the work. Need volunteers for each of the following sections (not limited to TC, _anyone_ knowledgeable in the area
- Ground truth chunk ids: `issue-339-excluded-001`
- Source titles: node@0.10 -> iojs@1.0.0 changelog

### Referenced chunks

#### issue-339-excluded-001

```text
Issue: node@0.10 -> iojs@1.0.0 changelog

Problem:
TC meeting today decided it would be good to have at least a broad-strokes changes document to show what's different in this release but we have to divide the work.

Need volunteers for each of the following sections (not limited to TC, _anyone_ knowledgeable in the area can do it), please post a comment and say which module you're doing, then when you're done post a link to wherever you've prepared your document and I'll aggregate it into a single format. Please use Markdown:
- [ ] assert
- [ ] buffer & smalloc (I believe that's a logical grouping)
- [ ] child_process
- [ ] cluster
- [ ] console
- [ ] crypto
- [ ] dgram
- [ ] dns
- [ ] domain
- [ ] events
- [ ] fs
- [ ] http & https
- [ ] module (module system in general)
- [ ] net
- [ ] os
- [ ] path
- [ ] process
- [ ] querystring
- [ ] repl
- [ ] stream
- [ ] sys
- [ ] timers
- [ ] tls
- [ ] url
- [ ] util
- [ ] vm
- [ ] zlib

also a section on major V8 changes would be good, that could be split up to:
- [ ] language features
- [ ] other V8 changes to expect

Writing should be concise and user-facing, not a bunch of commit log entries. What should people expect when they try this new beast out? What to look for, what they'll need to take into account when adapting their code, what new features to experiment with.
```

### Review checklist

- [ ] Is the question a realistic maintainer/user question?
- [ ] Is the ideal answer grounded in the referenced chunk?
- [ ] Is the chunk ID correct?
- [ ] Does the answer avoid broken raw markdown?
- [ ] Should this row be kept, rewritten, or replaced?
