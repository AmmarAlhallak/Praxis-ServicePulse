import json,urllib.request,urllib.parse,pathlib,concurrent.futures,hashlib
root=pathlib.Path('data/raw'); commit=json.loads(pathlib.Path('research/gitlab_commit.json').read_text())['id'];tree=json.loads(pathlib.Path('research/gitlab_tree.json').read_text());files=[x['path'] for x in tree if x['path'].endswith('.parquet')]
expected={x['path']:x['id'] for x in tree if x['type']=='blob'}
def hashes(path):
 sha=hashlib.sha256();blob=hashlib.sha1();blob.update(f'blob {path.stat().st_size}\0'.encode())
 with path.open('rb') as handle:
  for chunk in iter(lambda:handle.read(4*1024*1024),b''):
   sha.update(chunk);blob.update(chunk)
 return sha.hexdigest(),blob.hexdigest()
def download(p):
 dest=root/pathlib.Path(p).relative_to('data/dataset');dest.parent.mkdir(parents=True,exist_ok=True)
 url='https://lab.compute.dtu.dk/api/v4/projects/1804/repository/files/'+urllib.parse.quote(p,safe='')+'/raw?ref='+commit
 try:
  if not dest.exists() or hashes(dest)[1] != expected[p]:
   temporary=dest.with_suffix('.parquet.part')
   with urllib.request.urlopen(url,timeout=120) as response, temporary.open('wb') as output:
    for chunk in iter(lambda:response.read(4*1024*1024),b''):output.write(chunk)
   if hashes(temporary)[1] != expected[p]:raise ValueError('Git-Blob-Prüfsumme stimmt nicht überein')
   temporary.replace(dest)
  with dest.open('rb') as handle:
   if handle.read(4)!=b'PAR1':raise ValueError('Keine Parquet-Datei; möglicherweise Git-LFS-Zeiger')
  sha,blob=hashes(dest)
  return dict(path=str(dest),source=p,url=url,commit=commit,bytes=dest.stat().st_size,sha256=sha,git_blob_sha1=blob,git_blob_verified=blob==expected[p])
 except Exception as e:return dict(path=str(dest),error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(download,files))
pathlib.Path('research/download_manifest.json').write_text(json.dumps(results,indent=2))
print('Files',len(results),'Bytes',sum(x.get('bytes',0) for x in results),'Errors',[x for x in results if 'error' in x])
