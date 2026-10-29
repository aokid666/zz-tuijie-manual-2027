"""Parse only original upper-book exercises on GitHub; written correction answers stay self-assessed."""
import pathlib,json,re,difflib,collections,math
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'_site/data';OUT.mkdir(parents=True,exist_ok=True)
ID='tuijie-manual-exercises';SID='tuijie-manual-upper';BASE='https://aokid666.github.io/zz-tuijie-manual-2027/'
d=json.loads((ROOT/'data'/f'{SID}.json').read_text());ps=d['pages'];cfg=json.loads((ROOT/'tools/reviewed-exercises.json').read_text());J={int(p):v for p,v in cfg['judgementHints'].items()};MATCH={int(p):v for p,v in cfg['matching'].items()};BLANK={int(p):v for p,v in cfg['blankHints'].items()}
TEST={19,20,31,32,38,43,53,54,58,86,87,98,99,104,119,120,131,132,143,144,157,158,181,182,194,195,208,209,221,222,234,235,244,245};qs=[];errors=[];audit=[];blocks=[19,31,38,43,53,58,86,98,104,119,131,143,157,181,194,208,221,234,244]
def dump(name,x):
 s=json.dumps(x,ensure_ascii=False,separators=(',',':'));(ROOT/'data'/name).write_text(s);(OUT/name).write_text(s)
def norm(t):return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',t)
def mod(p):return '马克思主义基本原理' if p<74 else '毛泽东思想和中国特色社会主义理论体系概论' if p<106 else '习近平新时代中国特色社会主义思想概论' if p<162 else '中国近现代史纲要' if p<210 else '思想道德与法治'
def rows(p):
 pg=ps[p-1];ls=[dict(l) for l in pg['lines']]+cfg['corrections'].get(str(p),[]);ls.sort(key=lambda l:(round(l['b'][1]/3),l['b'][0]));return [l for l in ls if 40<l['b'][1]<pg['height']-40]
def zone(p,phrase):
 ls=rows(p);i=next(i for i,l in enumerate(ls) if phrase in l['t']);start=ls[i]['b'][3]+2;end=min((l['b'][1]-3 for l in ls[i+1:] if re.search(r'^[123][.．、]\s*请你|^提示|^请根据|^扫码',l['t'])),default=ps[p-1]['height']-45);return [l for l in ls if start<l['b'][1]<end],start,end
def numbered(ls):
 groups=[]
 for l in ls:
  h=re.match(r'^[（(]\s*(\d+)\s*[）)]\s*(.*)',l['t'])
  if h:groups.append({'no':int(h[1]),'text':h[2],'rows':[l]})
  elif groups:groups[-1]['text']+=l['t'];groups[-1]['rows'].append(l)
 return groups
def crop(p,rs):
 pg=ps[p-1];y=max(35,min(l['b'][1] for l in rs)-4);bot=min(pg['height']-35,max(l['b'][3] for l in rs)+7);return {'page':p,'b':[25,y,pg['width']-50,bot-y]}
# Query only genuine正文 pages; self-test pages contain intentionally incorrect statements.
corpus=[p for p in ps if p['page']>=11 and p['page'] not in TEST]
WINDOWS=collections.defaultdict(list)
for p in corpus:
 rs=[l for l in p['lines'] if 40<l['b'][1]<p['height']-35]
 for i in range(len(rs)):
  chunk=rs[max(0,i-1):i+6];t=norm(''.join(l['t'] for l in chunk));grams={t[j:j+3] for j in range(len(t)-2)};WINDOWS[mod(p['page'])].append((p,chunk,t,grams))
def evidence(query,module):
 q=norm(query);qgrams={q[j:j+3] for j in range(len(q)-2)};candidates=[]
 shortlist=sorted(WINDOWS[module],key=lambda row:len(qgrams & row[3]),reverse=True)[:45]
 for p,chunk,t,grams in shortlist:
  matches=difflib.SequenceMatcher(None,q,t,autojunk=False).get_matching_blocks();run=max((m.size for m in matches),default=0);covered=sum(m.size for m in matches if m.size>=3);score=run*2+covered-len(t)*.006
  if run>=4:candidates.append((score,run,p,chunk))
 if not candidates:return None
 _,run,p,chunk=max(candidates,key=lambda x:(x[0],x[1]));quote='\n'.join(l['t'] for l in chunk);return crop(p['page'],chunk),{'source':SID,'page':p['page'],'quote':quote,'method':'original-exercise-corresponding-handbook-text'},run

def base(p,no,kind,stem,qrefs,queries):
 block=max(b for b in blocks if b<=p);title=next((l['t'] for l in ps[block-1]['lines'] if '背诵自测总结' in l['t']),'背诵自测总结');chapter=mod(p)+' · '+title.replace('背诵自测总结','自测');proof=[];refs=[]
 for hi,hint in enumerate(queries):
  binding=cfg.get('evidenceBindings',{}).get(f'{p}/{kind}/{no}') or (cfg.get('matchingEvidenceBindings',{}).get(str(p),{}).get(str(hi+1)) if kind=='matching' else None)
  found=None
  if binding:
   pn,anchor,*note=binding;pg=ps[pn-1];rs=[l for l in pg['lines'] if 40<l['b'][1]<pg['height']-35];idx=next(i for i,l in enumerate(rs) if anchor in l['t']);chunk=rs[max(0,idx-2):idx+8];e={'source':SID,'page':pn,'quote':'\n'.join(l['t'] for l in chunk),'method':'reviewed-handbook-passage'}
   if note:e['note']=note[0]
   found=(crop(pn,chunk),e,len(norm(anchor)))
  else:found=evidence(hint,mod(p))
  if found:
   r,e,run=found
   if not any(x['page']==r['page'] and x['b']==r['b'] for x in refs):refs.append(r);proof.append(e)
   audit.append({'p':p,'no':no,'kind':kind,'query':hint,'sourcePage':r['page'],'longestRun':run,'quote':e['quote']})
  else:errors.append(f'{p}/{kind}/{no}: no source passage for {hint}')
 q={'id':f'pr-{ID}-{kind}-{p:03}-{no:02}','bookId':ID,'type':'matching' if kind=='matching' else 'written','source':'p','moduleIdx':14,'module':'腿姐背诵手册自测','subject':mod(p),'chapter':chapter,'chapterTitle':chapter,'section':{'judgement':'判断并订正','blank':'原书填空','matching':'关键词连线','drawing':'画图自测'}[kind],'no':no,'originalNo':no,'stem':stem,'options':{},'multi':False,'answer':'','qRefs':qrefs,'keyRefs':refs,'analysis':[{'k':'手册正文对照（请据此核对原题）','t':'\n\n'.join((e.get('note','')+'\n' if e.get('note') else '')+'上册 PDF 第 '+str(e['page'])+' 页：\n'+e['quote'] for e in proof)}],'extraLectures':proof,'kPages':[],'sPages':[],'mRefs':[],'aPages':[],'aCrops':[],'sourceWarning':'原书自测答案另有二维码。本页提供同册正文对照，不冒充二维码官方解析；判断订正、填空与画图由本人核对后自评。','extractionNote':'准确空白、表格与版面以原图为准。'};qs.append(q);return q
for p,hints in J.items():
 ls,_,_=zone(p,'判断下列表述');gs=numbered(ls)
 if [g['no'] for g in gs]!=list(range(1,len(hints)+1)):errors.append(f'{p}: judgement boundaries {[g["no"] for g in gs]}')
 for g,hint in zip(gs,hints):base(p,g['no'],'judgement','请判断下列表述是否正确，并对错误表述进行订正：\n'+g['text'],[crop(p,g['rows'])],[hint])
for p,hints in BLANK.items():
 ls,start,end=zone(p,'请你对重点内容')
 if p==32 and ls and not re.match(r'^[（(]\s*1',ls[0]['t']):ls[0]['t']='（1）______'+ls[0]['t']
 gs=numbered(ls)
 if [g['no'] for g in gs]!=list(range(1,len(hints)+1)):errors.append(f'{p}: blank boundaries {[g["no"] for g in gs]}')
 for i,(g,hint) in enumerate(zip(gs,hints)):
  r=crop(p,g['rows']);bottom=gs[i+1]['rows'][0]['b'][1]-3 if i+1<len(gs) else min(end,max(l['b'][3] for l in g['rows'])+16);r['b'][3]=bottom-r['b'][1]
  base(p,g['no'],'blank','请按原图填写空白，可在图上手写或输入答案：\n'+g['text'],[r],[hint])
for p,keys in MATCH.items():
 ls,start,end=zone(p,'连线对应');split=ps[p-1]['width']*.52;left=numbered([l for l in ls if l['b'][0]<split]);right=[];rr=[l for l in ls if l['b'][0]>=split];col=min(l['b'][0] for l in rr)
 for l in rr:
  t=re.sub(r'^[①-⑳?@]|^\d{1,2}(?!\d)','',l['t']).strip()
  if l['b'][0]<=col+5 or not right:right.append({'text':t,'rows':[l]})
  else:right[-1]['text']+=t;right[-1]['rows'].append(l)
 if len(left)!=len(keys) or len(right)!=len(keys):errors.append(f'{p}: matching columns left={len(left)} right={len(right)} expected={len(keys)}')
 if len(left)!=len(keys) or len(right)!=len(keys):continue
 pairs=[g['text']+'：'+right[key-1]['text'] for g,key in zip(left,keys)];q=base(p,1,'matching','请对下列关键词进行连线对应（支持连线和填序号两种方式）。',[crop(p,ls)],pairs)
 q.update(left=[{'key':chr(65+i),'text':g['text']} for i,g in enumerate(left)],right=[{'key':str(i+1),'text':g['text']} for i,g in enumerate(right)],matchMap={chr(65+i):[str(k)] for i,k in enumerate(keys)},multiMatch=False)
 q['analysis'].insert(0,{'k':'按同册正文核对的关键词对应','t':'\n'.join(f'{chr(65+i)} → {keys[i]}：'+pair for i,pair in enumerate(pairs))})
p=54;ls=rows(p);rs=[l for l in ls if l['b'][1]>=next(l['b'][1] for l in ls if '请你画出' in l['t']) and l['b'][1]<510];base(p,1,'drawing','请画出必要劳动、剩余劳动的“四宫格”，并写出剩余价值的唯一来源。',[crop(p,rs)],['必要劳动时间；剩余劳动时间；剩余价值的唯一源泉是雇佣工人的剩余劳动'])
qs.sort(key=lambda q:(q['qRefs'][0]['page'],q['qRefs'][0]['b'][1]));counts=dict(collections.Counter(q['type'] for q in qs));sections=dict(collections.Counter(q['section'] for q in qs));report={'questions':len(qs),'counts':counts,'sections':sections,'errors':errors,'sourcePages':len(ps),'officialQRCodeAnswerObtained':False,'method':'original exercises, same-book text evidence, explicit self-assessment for written corrections','passages':audit}
dump('exercise-report.json',report)
if errors:raise RuntimeError(str(errors))
assert len(qs)==189 and sections=={'判断并订正':152,'关键词连线':17,'原书填空':19,'画图自测':1},sections
urls=[BASE+f'img/{SID}/{p["page"]:03}.{p["ext"]}' for p in ps];book={'id':ID,'title':'腿姐背诵手册 · 专题自测','kind':'exercise','count':len(qs),'counts':counts,'pages':len(ps),'pageSizes':[{'width':p['width'],'height':p['height']} for p in ps],'pageUrls':urls,'pdfParts':[{'firstPage':1,'lastPage':245,'url':BASE+'pdf/'+SID+'.pdf'}],'sourceBase':BASE,'url':BASE+'pdf/'+SID+'.pdf','sha256':d['source']['sha256'],'chapters':[{'key':ch,'title':ch,'count':sum(q['chapter']==ch for q in qs),'firstPage':next(q['qRefs'][0]['page'] for q in qs if q['chapter']==ch)} for ch in dict.fromkeys(q['chapter'] for q in qs)]}
dump('book.json',book);dump(ID+'.json',{'bookId':ID,'questions':qs,'pages':[{'page':p['page'],'width':p['width'],'height':p['height'],'text':p['text']} for p in ps]});print({k:v for k,v in report.items() if k!='passages'},flush=True)
