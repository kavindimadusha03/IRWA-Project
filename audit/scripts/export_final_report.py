"""Export the local audit report to printable HTML and editable DOCX using only the standard library."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,html,json,re,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'; SOURCE=AUDIT/'final_report.md'
text=SOURCE.read_text(encoding='utf-8'); manifest=json.loads((AUDIT/'final_report_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)==manifest['report_sha256'],'Report changed after manifest generation; review it before export'
assert not (AUDIT/'final_report.docx').exists() and not (AUDIT/'final_report.html').exists(),'Existing exports must be reviewed before replacement'
blocks=[]; lines=text.splitlines(); i=0
while i<len(lines):
 line=lines[i]
 if not line.strip(): i+=1; continue
 heading=re.match(r'^(#{1,6}) (.+)$',line)
 if heading: blocks.append(('heading',len(heading[1]),heading[2])); i+=1; continue
 if line.startswith('|'):
  rows=[]
  while i<len(lines) and lines[i].startswith('|'):
   cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
   if not all(re.fullmatch(r':?-+:?',x) for x in cells): rows.append(cells)
   i+=1
  assert rows and all(len(r)==len(rows[0]) for r in rows)
  blocks.append(('table',rows)); continue
 if line.startswith('```'):
  code=[]; i+=1
  while i<len(lines) and not lines[i].startswith('```'): code.append(lines[i]); i+=1
  blocks.append(('code','\n'.join(code))); i+=1; continue
 parts=[]
 while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,6} |\||```)',lines[i]): parts.append(lines[i]); i+=1
 blocks.append(('paragraph','\n'.join(p.rstrip() if p.endswith('  ') else p for p in parts)))

def inline_parts(value):
 pattern=r'(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*)'; position=0
 for match in re.finditer(pattern,value):
  if match.start()>position: yield ('text',value[position:match.start()],None)
  token=match[0]
  if token.startswith('['):
   label,target=re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)',token).groups(); yield ('link',label,target)
  elif token.startswith('`'): yield ('code',token[1:-1],None)
  else: yield ('bold',token[2:-2],None)
  position=match.end()
 if position<len(value): yield ('text',value[position:],None)

def html_inline(value):
 result=[]
 for kind,label,target in inline_parts(value):
  label=html.escape(label).replace('\n','<br>')
  if kind=='link': result.append('<a href="'+html.escape(target,quote=True)+'">'+label+'</a>')
  elif kind=='bold': result.append('<strong>'+label+'</strong>')
  elif kind=='code': result.append('<code>'+label+'</code>')
  else: result.append(label)
 return ''.join(result)
body=[]
for block in blocks:
 if block[0]=='heading':
  level,value=block[1:]; body.append(f'<h{level}>'+html_inline(value)+f'</h{level}>')
 elif block[0]=='paragraph': body.append('<p>'+html_inline(block[1])+'</p>')
 elif block[0]=='code': body.append('<pre><code>'+html.escape(block[1])+'</code></pre>')
 else:
  rows=block[1]; body.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+html_inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>')
  for row in rows[1:]: body.append('<tr>'+''.join('<td>'+html_inline(c)+'</td>' for c in row)+'</tr>')
  body.append('</tbody></table></div>')
css='''@page { size:A4; margin:18mm; }
* { box-sizing:border-box; } body { margin:0 auto; padding:40px; max-width:1100px; color:#172337; background:#fff; font:16px/1.58 Georgia,serif; }
h1,h2,h3,h4 { font-family:Arial,sans-serif; line-height:1.25; color:#153c58; break-after:avoid; }
h1 { font-size:32px; margin:0 0 22px; } h2 { font-size:25px; margin:42px 0 18px; padding-bottom:8px; border-bottom:2px solid #d9e4eb; } h3 { font-size:19px; margin-top:28px; }
p { margin:0 0 14px; orphans:3; widows:3; } a { color:#005d8f; overflow-wrap:anywhere; text-decoration:underline; }
code { font:0.9em Consolas,monospace; background:#f0f4f7; padding:1px 3px; overflow-wrap:anywhere; } pre { white-space:pre-wrap; }
.table-wrap { overflow-x:auto; margin:16px 0 24px; } table { width:100%; border-collapse:collapse; table-layout:fixed; font:13px/1.45 Arial,sans-serif; }
th,td { border:1px solid #c8d6df; text-align:left; vertical-align:top; padding:9px; overflow-wrap:anywhere; } th { background:#e6eef3; color:#153c58; font-weight:700; } tbody tr:nth-child(even) { background:#f7f9fb; }
@media print { body { padding:0; max-width:none; font-size:10.5pt; line-height:1.4; } h1 { font-size:23pt; } h2 { font-size:17pt; break-before:page; margin-top:0; } h3 { font-size:12pt; } table { font-size:8.5pt; } th,td { padding:5pt; } thead { display:table-header-group; } tr { break-inside:avoid; } .table-wrap { overflow:visible; } a { color:inherit; } }
'''
html_doc='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>KnowGap AI — Individual AI Security Audit</title><style>'+css+'</style></head><body><main>\n'+'\n'.join(body)+'\n</main></body></html>\n'
(AUDIT/'final_report.html').write_text(html_doc,encoding='utf-8',newline='\n')

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'; R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'; REL='http://schemas.openxmlformats.org/package/2006/relationships'; XML='http://www.w3.org/XML/1998/namespace'
ET.register_namespace('w',W); ET.register_namespace('r',R)
def w(tag,attrs=None): return ET.Element('{'+W+'}'+tag,{'{'+W+'}'+k:str(v) for k,v in (attrs or {}).items()})
def sub(parent,tag,attrs=None): child=w(tag,attrs); parent.append(child); return child
rels=ET.Element('Relationships',xmlns=REL)
for ident,kind,target in [('rId1','styles','styles.xml'),('rId2','footer','footer1.xml'),('rId3','settings','settings.xml')]: ET.SubElement(rels,'Relationship',Id=ident,Type=R+'/'+kind,Target=target)
link_ids={}
def link_id(target):
 if target not in link_ids:
  ident='rId'+str(len(link_ids)+4); link_ids[target]=ident
  ET.SubElement(rels,'Relationship',Id=ident,Type=R+'/hyperlink',Target=target,TargetMode='External')
 return link_ids[target]
def add_run(parent,value,bold=False,code=False,hyperlink=False):
 run=sub(parent,'r'); prop=sub(run,'rPr')
 if bold: sub(prop,'b')
 if code: sub(prop,'rFonts',{'ascii':'Consolas','hAnsi':'Consolas'}); sub(prop,'sz',{'val':19})
 if hyperlink: sub(prop,'color',{'val':'005D8F'}); sub(prop,'u',{'val':'single'})
 pieces=value.split('\n')
 for n,piece in enumerate(pieces):
  if n: sub(run,'br')
  element=sub(run,'t'); element.set('{'+XML+'}space','preserve'); element.text=piece
 return run
def paragraph(parent,value,style=None,header=False):
 p=sub(parent,'p'); prop=sub(p,'pPr')
 if style: sub(prop,'pStyle',{'val':style})
 if header: sub(prop,'keepNext')
 for kind,label,target in inline_parts(value):
  if kind=='link':
   link=sub(p,'hyperlink'); link.set('{'+R+'}id',link_id(target)); add_run(link,label,hyperlink=True)
  else: add_run(p,label,bold=header or kind=='bold',code=kind=='code')
 return p
styles=w('styles'); defaults=sub(styles,'docDefaults'); rp=sub(sub(defaults,'rPrDefault'),'rPr'); sub(rp,'rFonts',{'ascii':'Calibri','hAnsi':'Calibri'}); sub(rp,'sz',{'val':22}); sub(rp,'lang',{'val':'en-GB'})
pp=sub(sub(defaults,'pPrDefault'),'pPr'); sub(pp,'spacing',{'after':120,'line':276,'lineRule':'auto'})
for ident,name,size,bold,color,outline in [('Normal','Normal',22,False,'172337',None),('Title','Title',40,True,'153C58',None),('Heading1','heading 1',32,True,'153C58',0),('Heading2','heading 2',25,True,'153C58',1),('Heading3','heading 3',23,True,'153C58',2),('TableText','Table Text',18,False,'172337',None),('Footer','Footer',18,False,'586776',None)]:
 style=sub(styles,'style',{'type':'paragraph','styleId':ident}); sub(style,'name',{'val':name})
 if ident=='Normal': style.set('{'+W+'}default','1')
 else: sub(style,'basedOn',{'val':'Normal'})
 prop=sub(style,'pPr')
 if outline is not None:
  sub(prop,'outlineLvl',{'val':outline}); sub(prop,'keepNext'); sub(prop,'keepLines'); sub(prop,'spacing',{'before':240,'after':140})
  if ident=='Heading1': sub(prop,'pageBreakBefore')
 if ident=='Title': sub(prop,'keepNext'); sub(prop,'spacing',{'after':260})
 if ident=='TableText': sub(prop,'spacing',{'after':60,'line':240,'lineRule':'auto'})
 rprop=sub(style,'rPr'); sub(rprop,'sz',{'val':size}); sub(rprop,'color',{'val':color})
 if bold: sub(rprop,'b')
doc=w('document'); content=sub(doc,'body')
for block in blocks:
 if block[0]=='heading':
  level,value=block[1:]; paragraph(content,value,'Title' if level==1 else 'Heading'+str(min(level-1,3)))
 elif block[0]=='paragraph': paragraph(content,block[1])
 elif block[0]=='code': paragraph(content,'`'+block[1]+'`')
 else:
  rows=block[1]; count=len(rows[0]); tbl=sub(content,'tbl'); prop=sub(tbl,'tblPr'); sub(prop,'tblW',{'w':0,'type':'auto'}); sub(prop,'tblLayout',{'type':'fixed'})
  borders=sub(prop,'tblBorders')
  for side in ('top','left','bottom','right','insideH','insideV'): sub(borders,side,{'val':'single','sz':4,'color':'C8D6DF'})
  margin=sub(prop,'tblCellMar')
  for side in ('top','left','bottom','right'): sub(margin,side,{'w':70,'type':'dxa'})
  widths=[int(9860/count)]*count
  if count==2: widths=[3100,6760]
  if count==4 and rows[0][0]=='Test ID': widths=[700,2100,4860,2200]
  grid=sub(tbl,'tblGrid')
  for width in widths: sub(grid,'gridCol',{'w':width})
  for row_index,row in enumerate(rows):
   tr=sub(tbl,'tr'); trp=sub(tr,'trPr'); sub(trp,'cantSplit')
   if row_index==0: sub(trp,'tblHeader')
   for col,value in enumerate(row):
    tc=sub(tr,'tc'); tcp=sub(tc,'tcPr'); sub(tcp,'tcW',{'w':widths[col],'type':'dxa'}); sub(tcp,'vAlign',{'val':'top'})
    if row_index==0: sub(tcp,'shd',{'fill':'E6EEF3'})
    paragraph(tc,value,'TableText',header=row_index==0)
  paragraph(content,'')
section=sub(content,'sectPr'); footref=sub(section,'footerReference',{'type':'default'}); footref.set('{'+R+'}id','rId2'); sub(section,'pgSz',{'w':11906,'h':16838}); sub(section,'pgMar',{'top':1023,'right':1023,'bottom':1023,'left':1023,'header':360,'footer':480,'gutter':0})
footer=w('ftr'); p=paragraph(footer,'KnowGap AI | Individual audit | Page ','Footer'); sub(p.find('{'+W+'}pPr'),'jc',{'val':'right'}); field=sub(p,'fldSimple',{'instr':'PAGE'}); add_run(field,'1')
settings=w('settings'); sub(settings,'updateFields',{'val':'true'})
content_types=ET.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
for extension,mimetype in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('xml','application/xml')]: ET.SubElement(content_types,'Default',Extension=extension,ContentType=mimetype)
for part,kind in [('/word/document.xml','document.main'),('/word/styles.xml','styles'),('/word/footer1.xml','footer'),('/word/settings.xml','settings')]: ET.SubElement(content_types,'Override',PartName=part,ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.'+kind+'+xml')
package_rels=ET.Element('Relationships',xmlns=REL); ET.SubElement(package_rels,'Relationship',Id='rId1',Type=R+'/officeDocument',Target='word/document.xml')
parts={'[Content_Types].xml':content_types,'_rels/.rels':package_rels,'word/document.xml':doc,'word/styles.xml':styles,'word/footer1.xml':footer,'word/settings.xml':settings,'word/_rels/document.xml.rels':rels}
with zipfile.ZipFile(AUDIT/'final_report.docx','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name,element in parts.items(): archive.writestr(name,ET.tostring(element,encoding='utf-8',xml_declaration=True))
# Validate format structure and literal content parity without importing application modules.
with zipfile.ZipFile(AUDIT/'final_report.docx') as archive:
 assert archive.testzip() is None
 for name in parts: ET.fromstring(archive.read(name))
 loaded=ET.fromstring(archive.read('word/document.xml'))
 def visible(value): return ''.join(label for _,label,_ in inline_parts(value)).replace('\n','')
 expected=[]
 for block in blocks:
  if block[0]=='heading': expected.append(visible(block[2]))
  elif block[0] in ('paragraph','code'): expected.append(visible(block[1]))
  else:
   for row in block[1]: expected.extend(visible(cell) for cell in row)
 actual=''.join(loaded.itertext())
 assert actual==''.join(expected),'DOCX text differs from Markdown source'
 assert len(loaded.findall('.//{'+W+'}hyperlink'))==sum(1 for block in blocks for value in ([block[2]] if block[0]=='heading' else [block[1]] if block[0] in ('paragraph','code') else [cell for row in block[1] for cell in row]) for kind,_,_ in inline_parts(value) if kind=='link')
manifest['exports']={name:{'sha256':sha(AUDIT/name),'bytes':(AUDIT/name).stat().st_size} for name in ['final_report.html','final_report.docx']}
manifest['exported_at_utc']=datetime.now(timezone.utc).isoformat(); manifest['export_validation']={'markdown_to_DOCX_text_parity':True,'all_DOCX_XML_parts_parse':True,'DOCX_zip_integrity':True,'HTML_external_scripts_or_assets':False,'format':'Editable OOXML Word document and self-contained printable HTML; evidence links remain relative to audit directory','rendering_limit':'Structure and content validated programmatically; not visually rendered in Microsoft Word or a browser during export'}
(AUDIT/'final_report_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'exports':manifest['exports'],'blocks':len(blocks),'tables':sum(b[0]=='table' for b in blocks),'hyperlink_targets':len(link_ids),'content_parity':True},indent=2))
