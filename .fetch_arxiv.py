import urllib.request
url = "https://arxiv.org/list/cs.IR/recent?skip=0&show=100"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=60) as r:
    data = r.read()
open("/Users/zehaoxu/ResearchCapsule/.arxiv_ir.html", "wb").write(data)
print("bytes", len(data), "status", r.status)
