# -*- encoding: utf-8 -*-
# Converts non-localized python/django project to use with django i18n
# initially has been created for Russian, may be adopted to any language having
# non-ascii specific codes or any other specific recognized using regular expressions

import re
import os
import argparse
import polib
import cStringIO as StringIO
import datetime
import sys

#PYTHON_COMMENT_RE = re.compile(ur'(?m)(?P<c>#.*?)$')
#PYTHON_LONG_STRING_RE = re.compile(ur'(?P<b>([\']{3,3}|[\"]{3,3}))(?P<s>(.|[\r\n])*?)(?<![\\])(?P=b)')
#PYTHON_SHORT_STRING1_RE = re.compile(ur'(?P<b>(\'))(?P<s>(((?<=[\\]).)|[\r\n]|[^\'])*?)(?<![\\])(?P=b)')
#PYTHON_SHORT_STRING2_RE = re.compile(ur'(?P<b>(\"))(?P<s>(((?<=[\\]).)|[\r\n]|[^\"])*?)(?<![\\])(?P=b)')
#EMPTY_RE = re.compile(ur'\s*')

class html_processor:
    #STRING_RE = re.compile(ur'(?P<b>(([%][}]|([}][}])|[>])))(?P<s>(.|[\r\n])+?)(?P<e>(([{][%]|([{][{])|[<])))')
    #STRING_RE = re.compile(ur'(?P<b>(([%][}]|([}][}])|[>])))(?P<s>(.|[\r\n])*?)(?P<e>(([{][%])|([{][{])|[<]))')
    CDATA_START_RE = re.compile(ur'\<\!\[CDATA\[')
    CDATA_STOP_RE = re.compile(ur'\]\]\>')
    COMMENT_START_RE = re.compile(ur'\<\!--')
    COMMENT_STOP_RE = re.compile(ur'--\>')
    KW_START_RE = re.compile(ur'[{][%]')
    KW_STOP_RE = re.compile(ur'[%][}]')
    VR_START_RE = re.compile(ur'[{][{]')
    VR_STOP_RE = re.compile(ur'[}][}]')
    TG_START_RE = re.compile(ur'\<\s?/?\s?[a-zA-Z0-9_-]+')
    TG_ATTR_RE = re.compile(ur'''\s[a-zA-Z0-9_-]+\s?=\s?(("[^"]*")|('[^']*')|([^\s]))''')
    TG_STOP_RE = re.compile(ur'/?\s?\>')
    @staticmethod
    def find_strings(buf):
        strings = []
        fromstart = 0
        while True:
            p = None
            p_e = None
            p_comment = html_processor.COMMENT_START_RE.search(buf,fromstart)
            if p_comment:
                p_comment_end = html_processor.COMMENT_STOP_RE.search(buf,p_comment.end())
                if buf[fromstart:p_comment.start()].isspace():
                    #print u"{%s}: comment found, skipping: %s-%s [%s]" % (fromstart,p_comment.start(),p_comment_end.end(),buf[p_comment.start():p_comment_end.end()])
                    fromstart = p_comment_end.end()
                    continue
                p = p_comment
                p_e = p_comment_end
            #if p_comment:
            #    print u"{%s}: DEBUG, comment not reached yet: [[[%s]]]" % (fromstart,buf[fromstart:p_comment.start()])
            p_cdata = html_processor.CDATA_START_RE.search(buf,fromstart)
            if p_cdata:
                p_cdata_end = html_processor.CDATA_STOP_RE.search(buf,p_cdata.end())
                if buf[fromstart:p_cdata.start()].isspace():
                    #print u"{%s}: cdata found, skipping: %s-%s [%s]" % (fromstart,p_cdata.start(),p_cdata_end.end(),buf[p_cdata.start():p_cdata_end.end()])
                    fromstart = p_cdata_end.end()
                    continue
                if not p or p.start() > p_cdata.start():
                    p = p_cdata
                    p_e = p_cdata_end
            p_kw = html_processor.KW_START_RE.search(buf,fromstart)
            #p_vr = html_processor.VR_START_RE.search(buf,fromstart)
            p_tg = html_processor.TG_START_RE.search(buf,fromstart)
            if p_kw:
                if not p or p.start() > p_kw.start():
                    p = p_kw
                    p_e = html_processor.KW_STOP_RE.search(buf,p.end())
            #if p_vr:
            #    if not p or p.start() > p_vr.start():
            #        p = p_vr
            #        p_e = html_processor.VR_STOP_RE.search(buf,p.end())
            if p_tg:
                if not p or p.start() > p_tg.start():
                    p = p_tg
                    p1 = p
                    p_a = html_processor.TG_STOP_RE.search(buf,p1.end())
                    while p_a:
                        if not buf[p1.end():p_a.start()].isspace():
                            break
                        p1 = p_a
                        p_a = html_processor.TG_STOP_RE.search(buf,p1.end())
                    p_e = html_processor.TG_STOP_RE.search(buf,p1.end())
            if not p:
                break
            #what = 'kw' if p == p_kw else 'vr' if p == p_vr else 'tg' if p == p_tg else 'unknown'
            #print u"{%s}: found %s [%s:%s], getting string: %s-%s [%s]" % (fromstart,what,p.group(0),p_e.group(0),fromstart,p.start(),buf[fromstart:p.start()])
            ss = u' '.join([x for x in re.compile(u'\s').split(buf[fromstart:p.start()].strip()) if x])
            if ss:
                strings.append({
                    's':ss,
                    'start':fromstart,
                    'end':p.start(),
                })
            fromstart = p_e.end()
        return strings

    @staticmethod
    def replace_strings(buf,strings,trf_short,trf_block,htmlpreamble,jspreamble,django_po_path):
        buf0 = buf
        po = polib.pofile(django_po_path)
        back_ref = {}
        #print "FRESHPO:",len(freshpo)
        for i in xrange(len(po)):
            ent = po[i]
            if ent.msgstr:
                if ent.msgstr in back_ref:
                    back_ref[ent.msgstr].append(i)
                else:
                    back_ref[ent.msgstr] = [i,]
            if ent.msgstr_plural:
                for k in ent.msgstr_plural:
                    if ent.msgstr_plural[k] in back_ref:
                        back_ref[ent.msgstr_plural[k]].append(i)
                    else:
                        back_ref[ent.msgstr_plural[k]] = [i,]

        for sss in strings[-1::-1]: # avoid messing up of positions
            if sss['s'] in back_ref:
                msgid = po[back_ref[sss['s']][0]].msgid
                start = sss['start']
                end = sss['end']
                localtext = buf[start:end]
                needs_block = False
                has_quote = localtext.find("'") >= 0
                has_dquote = localtext.find('"') >= 0
                if html_processor.VR_START_RE.search(localtext) and html_processor.VR_STOP_RE.search(localtext):
                    needs_block = True
                elif has_quote and has_dquote:
                    needs_block = True
                rpl = ''
                if needs_block:
                    rpl = trf_block.decode('utf-8','replace') % msgid
                else:
                    if has_quote:
                        rpl = trf_short.decode('utf-8','replace') % (u'"%s"' % msgid)
                    else:
                        rpl = trf_short.decode('utf-8','replace') % (u"'%s'" % msgid)
                rpl = rpl.encode('utf-8')
                buf = buf[:start] + rpl + buf[end:]

        if buf0 != buf:
            buf = u''.join([s.decode('utf-8','replace')+u'\n' for s in htmlpreamble]) + buf
        pp = re.compile(u'\<script[^\>]*src=').search(buf)
        if pp:
            buf = buf[:pp.start(0)] + u''.join([jp.decode('utf-8','replace') + u'\n' for jp in jspreamble]) + buf[pp.start(0):]

        return buf

class py_processor:
    @staticmethod
    def find_start_of_comment(buf):
        p = buf.find('#')
        if p >= 0:
            return p

    @staticmethod
    def find_end_of_comment(buf,p0):
        p = buf.find('\n',p0)
        if p >= 0:
            return p
        return len(buf)

    @staticmethod
    def find_start_of_string(buf):
        eos = None
        for i in xrange(len(buf)):
            c = buf[i]
            if c == '"':
                eos = '"'
                break
            if c == "'":
                eos = "'"
                break
        if not eos:
            return None,None
        if buf[i:i+3] == eos*3:
            eos = eos*3
        return i,eos

    @staticmethod
    def find_end_of_string(buf,frm,eos):
        BS = '\\'
        if isinstance(buf,unicode):
            BS = unicode(BS)
            eos = unicode(eos)
        bs = False
        for i in xrange(frm,len(buf)):
            c = buf[i]
            if c == BS:
                bs = True
                continue
            if bs == True:
                bs = False
                continue
            if buf[i:i+len(eos)] == eos:
                break
        return i

    @staticmethod
    def process_bs(buf):
        BS = '\\'
        special = {
                '\\':'\\',
                "'":"'",
                '"':'"',
                'a':'\a',
                'b':'\b',
                'f':'\f',
                'n':'\n',
                'r':'\r',
                't':'\t',
                'v':'\v',
        }
        digits = dict([(c,int(c,16)) for c in '0123456789abcdefABCDEF'])
        r = ''
        CHR = chr
        if isinstance(buf,unicode):
            BS = unicode(BS)
            special = {
                u'\\':u'\\',
                u"'":u"'",
                u'"':u'"',
                u'a':u'\a',
                u'b':u'\b',
                u'f':u'\f',
                u'n':u'\n',
                u'r':u'\r',
                u't':u'\t',
                u'v':u'\v',
            }
            r = u''
            CHR = unichr
        bs = False
        long_special = False
        spc = ''
        nn = None
        hxl = None
        base = None
        for i in xrange(len(buf)):
            c = buf[i]
            if long_special:
                if c in digits and digits[c] < base:
                    nn += c
                    hxl -= 1
                    if not hxl:
                        try:
                            r += CHR(int(nn,base))
                        except:
                            r += BS+spc+nn
                        long_special = False
                    continue
                r += BS+spc+nn
                long_special = False
            if c == BS:
                bs = True
                continue
            if bs == True:
                if c in special:
                    r += special[c]
                    bs = False
                    continue
                if c == 'x':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 2
                    bs = False
                    continue
                if c == 'u':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 4
                    bs = False
                    continue
                if c == 'U':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 8
                    bs = False
                    continue
                if c in "01234567":
                    long_special = True
                    spc = c
                    nn = c
                    base = 8
                    hxl = 2
                    bs = False
                    continue
                r += c
                bs = False
                continue
            r += c
        if bs:
            r += BS
        if long_special:
            r += BS + spc + nn
        return r

    @staticmethod
    def find_strings(buf):
        strings = []
        linenum = 1
        fromstart = 0
        while buf:
            p0 = py_processor.find_start_of_comment(buf)
            p1,eos = py_processor.find_start_of_string(buf)
            #p0 = PYTHON_COMMENT_RE.search(buf)
            #p2 = PYTHON_SHORT_STRING_RE.search(buf)
            #p1 = PYTHON_LONG_STRING_RE.search(buf)
            if p0 != None and p1 != None:
                if p1 < p0:
                    p0 = None
                else:
                    p1 = None
            if p1 != None:
                pe = py_processor.find_end_of_string(buf,p1+len(eos),eos)
                linenum += len(buf[:pe+len(eos)].split('\n'))-1
                #print u"[%s] FOUND STR:%s" % (linenum,buf[p1:pe+len(eos)])
                ss = buf[p1+len(eos):pe]
                if not (p1 > 0 and buf[p1-1] in ('r','R')): # needs bs processing
                    ss = py_processor.process_bs(ss)
                strings.append({
                    's':ss,
                    'start':fromstart + p1,
                    'end':fromstart + pe + len(eos),
                })
                buf = buf[pe+len(eos):]
                fromstart += pe+len(eos)
                continue
            if p0 != None:
                pe = py_processor.find_end_of_comment(buf,p0+1)
                linenum += len(buf[:pe].split('\n'))-1
                #print u"[%s] FOUND CMT:%s" % (linenum,buf[p0:pe])
                #comments.append({
                #    'c':buf[p0:pe],
                #    'start':p0,
                #    'end':pe
                #})
                buf = buf[pe:]
                fromstart += pe
                continue
            buf = ''
        return strings

    @staticmethod
    def replace_strings(buf,strings,trf,pypreamble,django_po_path):
        buf0 = buf
        po = polib.pofile(django_po_path)
        back_ref = {}
        #print "FRESHPO:",len(freshpo)
        for i in xrange(len(po)):
            ent = po[i]
            if ent.msgstr:
                if ent.msgstr in back_ref:
                    back_ref[ent.msgstr].append(i)
                else:
                    back_ref[ent.msgstr] = [i,]
            if ent.msgstr_plural:
                for k in ent.msgstr_plural:
                    if ent.msgstr_plural[k] in back_ref:
                        back_ref[ent.msgstr_plural[k]].append(i)
                    else:
                        back_ref[ent.msgstr_plural[k]] = [i,]

        for sss in strings[-1::-1]: # avoid messing up of positions
            if sss['s'] in back_ref:
                msgid = po[back_ref[sss['s']][0]].msgid.encode('utf-8')
                start = sss['start']
                if start > 0 and buf[start-1] in 'rR':
                    start -= 1
                if start > 0 and buf[start-1] in 'uU':
                    start -= 1
                end = sss['end']
                buf = buf[:start] + trf+'('+ repr(msgid) + ')' + buf[end:]

        if buf0 != buf:
            preamble = [s.decode('utf-8','replace')+'\n' for s in pypreamble]
            bb = buf.splitlines(True)
            for i in xrange(len(bb)):
                if not re.match('^\s*#.*',bb[i]):
                    break
            buf = ''.join(bb[:i]+preamble+bb[i:])

        return buf

class js_processor:
    @staticmethod
    def find_start_of_comment(buf):
        p = buf.find('//')
        if p >= 0:
            return p

    @staticmethod
    def find_start_of_ml_comment(buf):
        p = buf.find('/*')
        if p >= 0:
            return p

    @staticmethod
    def find_end_of_comment(buf,p0):
        p = buf.find('\n',p0)
        if p >= 0:
            return p
        return len(buf)

    @staticmethod
    def find_end_of_ml_comment(buf,p0):
        p = buf.find('*/',p0)
        if p >= 0:
            return p
        return len(buf)

    @staticmethod
    def find_start_of_string(buf):
        eos = None
        for i in xrange(len(buf)):
            c = buf[i]
            if c == '"':
                eos = '"'
                break
            if c == "'":
                eos = "'"
                break
        if not eos:
            return None,None
        return i,eos

    @staticmethod
    def find_end_of_string(buf,frm,eos):
        BS = '\\'
        if isinstance(buf,unicode):
            BS = unicode(BS)
            eos = unicode(eos)
        bs = False
        for i in xrange(frm,len(buf)):
            c = buf[i]
            if c == BS:
                bs = True
                continue
            if bs == True:
                bs = False
                continue
            if buf[i:i+len(eos)] == eos:
                break
        return i

    @staticmethod
    def process_bs(buf):
        BS = '\\'
        special = {
                '\\':'\\',
                "'":"'",
                '"':'"',
                'a':'\a',
                'b':'\b',
                'f':'\f',
                'n':'\n',
                'r':'\r',
                't':'\t',
                'v':'\v',
        }
        digits = dict([(c,int(c,16)) for c in '0123456789abcdefABCDEF'])
        r = ''
        CHR = chr
        if isinstance(buf,unicode):
            BS = unicode(BS)
            special = {
                u'\\':u'\\',
                u"'":u"'",
                u'"':u'"',
                u'a':u'\a',
                u'b':u'\b',
                u'f':u'\f',
                u'n':u'\n',
                u'r':u'\r',
                u't':u'\t',
                u'v':u'\v',
            }
            r = u''
            CHR = unichr
        bs = False
        long_special = False
        spc = ''
        nn = None
        hxl = None
        base = None
        for i in xrange(len(buf)):
            c = buf[i]
            if long_special:
                if c in digits and digits[c] < base:
                    nn += c
                    hxl -= 1
                    if not hxl:
                        try:
                            r += CHR(int(nn,base))
                        except:
                            r += BS+spc+nn
                        long_special = False
                    continue
                r += BS+spc+nn
                long_special = False
            if c == BS:
                bs = True
                continue
            if bs == True:
                if c in special:
                    r += special[c]
                    bs = False
                    continue
                if c == 'x':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 2
                    bs = False
                    continue
                if c == 'u':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 4
                    bs = False
                    continue
                if c == 'U':
                    long_special = True
                    spc = c
                    nn = ''
                    base = 16
                    hxl = 8
                    bs = False
                    continue
                if c in "01234567":
                    long_special = True
                    spc = c
                    nn = c
                    base = 8
                    hxl = 2
                    bs = False
                    continue
                r += c
                bs = False
                continue
            r += c
        if bs:
            r += BS
        if long_special:
            r += BS + spc + nn
        return r

    @staticmethod
    def find_strings(buf):
        strings = []
        linenum = 1
        fromstart = 0
        while buf:
            p0 = None
            p01 = js_processor.find_start_of_comment(buf)
            p02 = js_processor.find_start_of_ml_comment(buf)
            if p01 != None and p02 != None:
                if p01 < p02:
                    p0 = p01
                else:
                    p0 = p02
            p1,eos = js_processor.find_start_of_string(buf)
            #p0 = PYTHON_COMMENT_RE.search(buf)
            #p2 = PYTHON_SHORT_STRING_RE.search(buf)
            #p1 = PYTHON_LONG_STRING_RE.search(buf)
            if p0 != None and p1 != None:
                if p1 < p0:
                    p0 = None
                else:
                    p1 = None
            if p1 != None:
                pe = js_processor.find_end_of_string(buf,p1+len(eos),eos)
                linenum += len(buf[:pe+len(eos)].split('\n'))-1
                #print u"[%s] FOUND STR:%s" % (linenum,buf[p1:pe+len(eos)])
                ss = buf[p1+len(eos):pe]
                if not (p1 > 0 and buf[p1-1] in ('r','R')): # needs bs processing
                    ss = js_processor.process_bs(ss)
                strings.append({
                    's':ss,
                    'start':fromstart + p1,
                    'end':fromstart + pe + len(eos),
                })
                buf = buf[pe+len(eos):]
                fromstart += pe+len(eos)
                continue
            if p0 != None:
                pe = None
                if p0 == p01:
                    pe = js_processor.find_end_of_comment(buf,p0+1)
                else:
                    pe = js_processor.find_end_of_ml_comment(buf,p0+1)
                linenum += len(buf[:pe].split('\n'))-1
                #print u"[%s] FOUND CMT:%s" % (linenum,buf[p0:pe])
                #comments.append({
                #    'c':buf[p0:pe],
                #    'start':p0,
                #    'end':pe
                #})
                buf = buf[pe:]
                fromstart += pe
                continue
            buf = ''
        return strings

    @staticmethod
    def replace_strings(buf,strings,trf,django_po_path):
        buf0 = buf
        po = polib.pofile(django_po_path)
        back_ref = {}
        #print "FRESHPO:",len(freshpo)
        for i in xrange(len(po)):
            ent = po[i]
            if ent.msgstr:
                if ent.msgstr in back_ref:
                    back_ref[ent.msgstr].append(i)
                else:
                    back_ref[ent.msgstr] = [i,]
            if ent.msgstr_plural:
                for k in ent.msgstr_plural:
                    if ent.msgstr_plural[k] in back_ref:
                        back_ref[ent.msgstr_plural[k]].append(i)
                    else:
                        back_ref[ent.msgstr_plural[k]] = [i,]

        for sss in strings[-1::-1]: # avoid messing up of positions
            if sss['s'] in back_ref:
                msgid = po[back_ref[sss['s']][0]].msgid.encode('utf-8')
                start = sss['start']
                if start > 0 and buf[start-1] in 'rR':
                    start -= 1
                if start > 0 and buf[start-1] in 'uU':
                    start -= 1
                end = sss['end']
                buf = buf[:start] + trf+'('+ repr(msgid) + ')' + buf[end:]

        return buf


def store_strings(strings,django_po_path):
    try:
        os.makedirs(os.path.dirname(django_po_path))
    except:
        pass
    if os.path.exists(django_po_path):
        freshpo = polib.pofile(django_po_path)
        freshpo.metadata['PO-Revision-Date'] = '%s' % datetime.datetime.now()
        freshpo.metadata["X-Translated-Using"] = "convert_local_to_i18n 0.0.1"
    else:
        freshpo = polib.POFile()
        freshpo.metadata = {
            'Project-Id-Version': '1.0',
            'Report-Msgid-Bugs-To': 'you@example.com',
            'POT-Creation-Date': '%s' % datetime.datetime.now(),
            'PO-Revision-Date': '%s' % datetime.datetime.now(),
            'Last-Translator': 'you <you@example.com>',
            'Language-Team': 'English <yourteam@example.com>',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Transfer-Encoding': '8bit',
            "Plural-Forms": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)",
            "X-Translated-Using": "convert_local_to_i18n 0.0.1",
        }

    back_ref = {}
    #print "FRESHPO:",len(freshpo)
    for i in xrange(len(freshpo)):
        ent = freshpo[i]
        if ent.msgstr:
            if ent.msgstr in back_ref:
                back_ref[ent.msgstr].append(i)
            else:
                back_ref[ent.msgstr] = [i,]
        if ent.msgstr_plural:
            for k in ent.msgstr_plural:
                if ent.msgstr_plural[k] in back_ref:
                    back_ref[ent.msgstr_plural[k]].append(i)
                else:
                    back_ref[ent.msgstr_plural[k]] = [i,]

    counter = len(freshpo)
    for s in strings:
        if s in back_ref:
            continue
        #print "APPEND:",s
        freshpo.append(polib.POEntry(msgstr=unicode(s),msgid='NEEDS TO BE EDITED [%s]' % counter))
        counter += 1
    #print "FRESHPO - 2:",len(freshpo)
    freshpo.save(django_po_path)


def do_job_py(buf,path,target,args):
    #TODO: recognize file encoding
    if args.verbosity == 2: print "Processing py %s" % path
    buf = buf.decode('utf-8','replace')
    processor = py_processor()
    s = processor.find_strings(buf)
    if args.stage == 1:
        needs_to_have_i18n = []
        for sss in s:
            ss = sss['s']
            for rx in args.re:
                if rx.search(ss):
                    needs_to_have_i18n.append(ss)
        store_strings(needs_to_have_i18n,os.path.join(args.target,args.django_po_file))
    if args.stage == 2:
        s_back = {}
        for sss in s:
            if sss['s'] in s_back:
                s_back[sss['s']].append(sss)
            else:
                s_back[sss['s']] = [sss,]
        buf2 = processor.replace_strings(buf,s,args.pytrf,args.pypreamble,os.path.join(args.target,args.django_po_file))
        f = open(target,'w+b')
        f.write(buf2.encode('utf-8'))
        f.close()

    #o = file(target,'w+b')
    #o.write(buf)
    #o.close()

def do_job_html(buf,path,target,args):
    #TODO: recognize file encoding
    if args.verbosity == 2: print "Processing html %s" % path
    buf = buf.decode('utf-8','replace')
    processor = html_processor()
    s = processor.find_strings(buf)
    if args.stage == 1:
        needs_to_have_i18n = []
        for sss in s:
            ss = sss['s']
            for rx in args.re:
                if rx.search(ss):
                    needs_to_have_i18n.append(ss)
        store_strings(needs_to_have_i18n,os.path.join(args.target,args.django_po_file))
    if args.stage == 2:
        s_back = {}
        for sss in s:
            if sss['s'] in s_back:
                s_back[sss['s']].append(sss)
            else:
                s_back[sss['s']] = [sss,]
        buf2 = processor.replace_strings(buf,s,args.htmltrf_short,args.htmltrf_block,args.htmlpreamble,args.jspreamble,os.path.join(args.target,args.django_po_file))
        f = open(target,'w+b')
        f.write(buf2.encode('utf-8'))
        f.close()
    '''
    print "STRINGS FOUND for %s:" % path
    for sss in s:
        print "%s-%s:%s" % (sss['start'],sss['end'],sss['s'])
    exit(1)
    '''

def do_job_js(buf,path,target,args):
    if args.verbosity == 2: print "Processing js %s" % path

    buf = buf.decode('utf-8','replace')
    processor = js_processor()
    s = processor.find_strings(buf)
    if args.stage == 1:
        needs_to_have_i18n = []
        for sss in s:
            ss = sss['s']
            for rx in args.re:
                if rx.search(ss):
                    needs_to_have_i18n.append(ss)
        store_strings(needs_to_have_i18n,os.path.join(args.target,args.djangojs_po_file))
    if args.stage == 2:
        s_back = {}
        for sss in s:
            if sss['s'] in s_back:
                s_back[sss['s']].append(sss)
            else:
                s_back[sss['s']] = [sss,]
        buf2 = processor.replace_strings(buf,s,args.jstrf,os.path.join(args.target,args.djangojs_po_file))
        f = open(target,'w+b')
        f.write(buf2.encode('utf-8'))
        f.close()

def do_job(path,target,args):
    if not os.path.exists(path):
        print "ERROR: no such path:",path
        return False
    if re.match(".*/locale/.*",path):
         return True
    for skip in args.skip:
        if skip.match(path):
            return True
    if os.path.isdir(path):
        r = True
        for f in os.listdir(path):
            r = do_job(os.path.join(path,f),os.path.join(target,f),args) and r
        return r
    do_job_file(path,target,args)

def do_job_file(path,target,args):
    #if args.verbosity == 2: print "Processing %s" % path
    ext = os.path.splitext(path)[1]
    buf = ''
    if ext in args.pyext or ext in args.htmlext or ext in args.jsext:
        f = file(path,'rb')
        buf = f.read()
        f.close()
        try:
            os.makedirs(os.path.dirname(target))
        except:
            pass

    if ext in args.pyext:
        return do_job_py(buf,path,target,args)
    if ext in args.htmlext:
        return do_job_html(buf,path,target,args)
    if ext in args.jsext:
        return do_job_js(buf,path,target,args)
    return True

def RE(s):
    if isinstance(s,str):
        # TODO: recognize system encoding
        s = s.decode('utf-8','replace')
    return re.compile(s)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Converts not-internationalized locale-specific python/django project to use with django i18n',
        epilog=
        '''
This program should be started twice, with some extra hand-work between starts.

The first start collects all pieces of local text described by regex, and puts them
together into the django-specific django.po project file in the target location.
The django.po '''+'''location may be changed by --django-po-file parameter,'''+''' but always
is in the target directory.

After that stage, the programmer should open django.po file and fill empty msgid strings by
unique international strings manually.

The second program call reads existent django.po file, checks uniqueness of msgid strings and
copies all found files to the target directory, replacing found msgstr strings collected before,
by i18n-ready code composed from msgid strings.

Additionally, it appends some common i18n code to each processed file, even no any locale-specific
strings found in the file.
''',
    )
    
    parser.add_argument('path',metavar='PATH',type=str,help='Path to the project directory')
    parser.add_argument('target',metavar='TARGET',type=str,nargs='?',help='Path to save internationalized project directory, default PATH.i18n')
    parser.add_argument('--py-ext',metavar='PYEXT',action='append',dest='pyext',type=str,help='Select extensions to process as python files, default is "%(default)s"')
    parser.add_argument('--html-ext',metavar='HTMLEXT',action='append',dest='htmlext',type=str,help='Select extensions to process as html files, default is "%(default)s"')
    parser.add_argument('--js-ext',metavar='JSEXT',action='append',dest='jsext',type=str,help='Select extensions to process as javascript files, default is "%(default)s"')
    parser.add_argument('--py-trf',metavar='PYTRF',dest='pytrf',default='_',type=str,help='Python translation function name, default is "%(default)s"')
    parser.add_argument('--html-trf-short',metavar='HTMLTRF',dest='htmltrf_short',default='{%% trans %s %%}',type=str,help='HTML (short-form) translation code template using %%s as replacement for quoted text, default is "%(default)s" (note abount douple-percent for proper template encoding)')
    parser.add_argument('--html-trf-block',metavar='HTMLTRF',dest='htmltrf_block',default='{%% blocktrans %%}%s{%% endblocktrans %%}',type=str,help='HTML (block-form) translation code template using %%s as replacement for ORIGINAL text, default is "%(default)s" (note abount douple-percent for proper template encoding)')
    parser.add_argument('--js-trf',metavar='JSTRF',dest='jstrf',default='gettext',type=str,help='JavaScript translation function name, default is "%(default)s"')
    parser.add_argument('--py-preamble',metavar='PYPREAMBLE',action='append',dest='pypreamble',default=["from django.utils.translation import ugettext as _"],type=str,help='Python file preamble strings, default is adopted to django')
    parser.add_argument('--html-preamble',metavar='HTMLPREAMBLE',action='append',dest='htmlpreamble',default=["{% load i18n %}"],type=str,help='HTML file preamble strings, default is adpoted to django')
    parser.add_argument('--js-preamble',metavar='JSPREAMBLE',action='append',dest='jspreamble',default=['<script type="text/javascript" src="{% url django.views.i18n.javascript_catalog %}"></script>'],type=str,help='JS preamble inserted into the HTML file, default is adopted to django')
    parser.add_argument('--regex',metavar='RE',action='append',dest='re',type=RE,help='Regular expression(s) to recognize local-language file part, default for Russian')
    parser.add_argument('--skip',metavar='SKIP',action='append',dest='skip',type=RE,help='Regular expression(s) to match path to be skipped, default --skip ".*/static*." --skip ".*/migrations.*" --skip ".*/\\..*"')
    parser.add_argument('--django-po-file',metavar='FILE',type=str,dest='django_po_file',default='locale/ru/LC_MESSAGES/django.po',help='Name of the locale file where translations should be present, default is "%(default)s"')
    parser.add_argument('--djangojs-po-file',metavar='FILE',type=str,dest='djangojs_po_file',default='locale/ru/LC_MESSAGES/djangojs.po',help='Name of the locale file where JavaScript translations should be present, default is "%(default)s"')
    parser.add_argument('--stage',metavar='STAGE',type=int,choices=[1,2],dest='stage',default=0,help='Stage to process, default depends on django.po presence: 1 if not present and 2 if present')
    parser.add_argument('--verbosity',metavar='VERBOSITY',type=int,choices=[0,1,2],dest='verbosity',default=0,help='Program verbosity (0,1, or 2)')
    args = parser.parse_args()
    if not args.pyext:
        args.pyext = ['.py',]
    if not args.htmlext:
        args.htmlext = ['.html',]
    if not args.jsext:
        args.jsext = ['.js',]
    if not args.skip:
        args.skip = [RE('.*/static.*'),RE('.*/migrations.*'),RE(r'.*/\..*')]
    if not args.re:
        args.re = [RE(u'[а-яА-Я]')]
    if not args.target:
        args.target = args.path + '.i18n'
    if not args.stage:
        args.stage = 2 if os.path.exists(os.path.join(args.target,args.django_po_file)) else 1
    #if not args.pypreamble:
    #    args.pypreamble = ["from django.utils.translation import ugettext as _"]
    #if not args.htmlpreamble:
    #    args.htmlpreamble = ["{% load i18n %}"]
    #if not args.jspreamble:
    #    args.jspreamble = ['<script type="text/javascript" src="{% url django.views.i18n.javascript_catalog %}"></script>']
    if not do_job(args.path,args.target,args):
        exit(1)
    exit(0)
