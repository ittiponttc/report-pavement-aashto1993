# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger  v2.4

การปรับปรุง v2.4:
- แก้ไขการเลือกรูปผิด: user สามารถ preview และเลือก index รูปที่ต้องการ
- วิเคราะห์ aspect ratio ช่วยกรองรูปโครงสร้างชั้นทาง
- หน้าสรุปอยู่ท้ายสุด, แสดง 4 รูปแบบ (AC, JPCP, JRCP, CRCP)
- แก้ไข rId remapping (รูปภาพใน Word ไม่หาย)
"""

import streamlit as st
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from copy import deepcopy
from lxml import etree
from PIL import Image as PILImage
import io
import zipfile
import struct

# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️", layout="wide"
)
st.markdown("""
<style>
  .main-header {
    font-size:28px;font-weight:bold;text-align:center;padding:20px;
    background:linear-gradient(135deg,#667eea,#764ba2);
    color:white;border-radius:10px;margin-bottom:20px;
  }
  .sub-header{font-size:18px;color:#4A5568;text-align:center;margin-bottom:30px;}
  .section-header{
    background:#C6F6D5;padding:10px 15px;border-radius:8px;
    margin:15px 0 10px;font-weight:bold;color:#276749;
    border-left:4px solid #38A169;
  }
  .preview-box{
    background:#EBF8FF;border:2px solid #90CDF4;border-radius:8px;
    padding:10px;margin:5px 0;
  }
  .stButton>button{
    background:linear-gradient(135deg,#667eea,#764ba2);
    color:white;font-weight:bold;padding:10px 30px;
    border-radius:25px;border:none;font-size:16px;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Word helpers
# ─────────────────────────────────────────────────────────────────────────────

def set_thai_font(run, font_name="TH Sarabun New", size=15):
    run.font.name = font_name
    run.font.size = Pt(size)
    rPr = run._r.get_or_add_rPr()
    rf = rPr.get_or_add_rFonts()
    for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'):
        rf.set(qn(a), font_name)


def set_page_margins(sec):
    sec.page_width = Cm(21); sec.page_height = Cm(29.7)
    sec.orientation = WD_ORIENT.PORTRAIT
    for a in ('left_margin','right_margin','top_margin','bottom_margin'):
        setattr(sec, a, Cm(2.5))
    sec.header_distance = sec.footer_distance = Cm(1.25)


def _xml_elem(tag): return OxmlElement(tag)


def set_cell_format(cell, width_dxa, borders=True):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    # width
    w = _xml_elem('w:tcW')
    w.set(qn('w:w'), str(width_dxa)); w.set(qn('w:type'), 'dxa')
    tcPr.append(w)
    # vAlign top
    va = _xml_elem('w:vAlign'); va.set(qn('w:val'), 'top'); tcPr.append(va)
    # margin
    m = _xml_elem('w:tcMar')
    for s in ('top','bottom','left','right'):
        e = _xml_elem(f'w:{s}'); e.set(qn('w:w'),'80'); e.set(qn('w:type'),'dxa')
        m.append(e)
    tcPr.append(m)
    # borders
    if borders:
        b = _xml_elem('w:tcBorders')
        for s in ('top','bottom','left','right'):
            e = _xml_elem(f'w:{s}')
            e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4')
            e.set(qn('w:color'),'AAAAAA'); b.append(e)
        tcPr.append(b)


def set_table_props(tbl, total_dxa, col_widths):
    tbl_el = tbl._tbl
    tblPr = tbl_el.find(qn('w:tblPr')) or _xml_elem('w:tblPr')
    if tbl_el.find(qn('w:tblPr')) is None:
        tbl_el.insert(0, tblPr)
    tw = _xml_elem('w:tblW')
    tw.set(qn('w:w'), str(total_dxa)); tw.set(qn('w:type'), 'dxa')
    tblPr.append(tw)
    tg = _xml_elem('w:tblGrid')
    for w in col_widths:
        gc = _xml_elem('w:gridCol'); gc.set(qn('w:w'), str(w)); tg.append(gc)
    tbl_el.insert(1, tg)


# ─────────────────────────────────────────────────────────────────────────────
# Image tools
# ─────────────────────────────────────────────────────────────────────────────

RASTER_EXTS = ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif')


def extract_all_raster_images(file_bytes):
    """
    ดึงรูปภาพ raster ทั้งหมดจาก docx ตามลำดับในไฟล์
    Returns: list of dict {bytes, ext, filename, index, width, height, aspect}
    """
    result = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as z:
            media_files = sorted(f for f in z.namelist() if f.startswith('word/media/'))
            for idx, mf in enumerate(media_files):
                ext = mf.rsplit('.', 1)[-1].lower() if '.' in mf else ''
                if ext not in RASTER_EXTS:
                    continue
                img_bytes = z.read(mf)
                w, h = _get_dimensions(img_bytes, ext)
                aspect = h / w if (w and w > 0) else 1.0
                result.append({
                    'bytes': img_bytes, 'ext': ext,
                    'filename': mf.split('/')[-1],
                    'index': idx,
                    'width': w, 'height': h, 'aspect': aspect,
                    'size_kb': len(img_bytes) // 1024,
                })
    except Exception:
        pass
    return result


def _get_dimensions(img_bytes, ext):
    """ดึงขนาดรูปด้วย PIL"""
    try:
        img = PILImage.open(io.BytesIO(img_bytes))
        return img.width, img.height
    except Exception:
        pass
    # fallback: parse header manually
    try:
        if ext == 'png' and len(img_bytes) >= 24 and img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return (struct.unpack('>I', img_bytes[16:20])[0],
                    struct.unpack('>I', img_bytes[20:24])[0])
    except Exception:
        pass
    return None, None


def _img_to_streamlit_bytes(img_bytes, ext):
    """แปลงรูปเป็น bytes ที่ st.image รองรับ (PNG)"""
    try:
        buf = io.BytesIO()
        img = PILImage.open(io.BytesIO(img_bytes))
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        return img_bytes


def suggest_crosssection_index(images):
    """
    แนะนำ index รูปที่น่าจะเป็นรูปโครงสร้างชั้นทาง
    หลักการ: aspect ratio > 0.6 (ไม่ landscape มาก) + ไม่ใช่รูปที่ใหญ่สุด (nomograph)
    fallback: รูปสุดท้าย
    """
    if not images:
        return 0

    # กรองรูป landscape กว้างๆ ออก (nomograph มักมี aspect < 0.7)
    candidates = [i for i, img in enumerate(images) if img['aspect'] >= 0.65]

    if not candidates:
        # ถ้าทุกรูปเป็น landscape ใช้รูปสุดท้าย
        return len(images) - 1

    # จากผู้สมัคร เลือกรูปสุดท้าย (มักเป็นสรุปผล)
    return candidates[-1]


# ─────────────────────────────────────────────────────────────────────────────
# Document merge with rId fix
# ─────────────────────────────────────────────────────────────────────────────

def append_document(master_doc, source_doc):
    """
    Copy source_doc body → master_doc พร้อม remap rId รูปภาพ
    แก้ปัญหา: deepcopy element ยังอ้าง old rId ที่ชนกับ master_doc
    """
    rId_map = {}
    for rel_id, rel in source_doc.part.rels.items():
        if "image" in rel.reltype:
            try:
                new_rId = master_doc.part.relate_to(rel.target_part, rel.reltype)
                rId_map[rel_id] = new_rId
            except Exception:
                pass

    for element in source_doc.element.body:
        if element.tag.endswith('sectPr'):
            continue
        new_el = deepcopy(element)
        if rId_map:
            xml_str = etree.tostring(new_el, encoding='unicode')
            for old, new in rId_map.items():
                xml_str = xml_str.replace(f'r:embed="{old}"', f'r:embed="{new}"')
                xml_str = xml_str.replace(f'r:id="{old}"',    f'r:id="{new}"')
                xml_str = xml_str.replace(f'r:link="{old}"',  f'r:link="{new}"')
            try:
                new_el = etree.fromstring(xml_str)
            except Exception:
                pass
        master_doc.element.body.append(new_el)


# ─────────────────────────────────────────────────────────────────────────────
# Summary page
# ─────────────────────────────────────────────────────────────────────────────

def _insert_image_cell(cell, img_bytes):
    """ใส่รูปลงใน cell ลองหลายขนาด"""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for w_cm in (7.0, 6.2, 5.5, 4.8):
        try:
            run = para.add_run()
            run.add_picture(io.BytesIO(img_bytes), width=Cm(w_cm))
            return True
        except Exception:
            # ลบ run ที่ fail
            try:
                p = para._p
                for r in p.findall(qn('w:r')): p.remove(r)
            except Exception: pass
    r = para.add_run("[ไม่สามารถแสดงรูปภาพได้]")
    set_thai_font(r, size=12); r.font.italic = True
    return False


def add_pavement_summary_page(doc, summary_items, start_fig=11):
    """
    หน้าสรุปโครงสร้างชั้นทาง (ท้ายสุด)
    summary_items: list of (img_bytes, caption_str)
    """
    # หัวข้อ
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("สรุปโครงสร้างชั้นทางที่ออกแบบด้วยวิธี AASHTO 1993")
    set_thai_font(r, size=18); r.font.bold = True

    # คำอธิบาย
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    n = len(summary_items)
    r = p.add_run(
        "จากการคำนวณ/ออกแบบตามวิธี AASHTO 1993 สำหรับการออกแบบโครงสร้างชั้นทาง"
        " (Asphalt Concrete) และผิวทางคอนกรีต (Concrete Pavement)"
        " สามารถสรุปรูปแบบโครงสร้างชั้นทาง ดังแสดงในรูปที่ 2-{} ถึง รูปที่ 2-{}".format(
            start_fig, start_fig + n - 1)
    )
    set_thai_font(r, size=15)
    doc.add_paragraph()

    if not summary_items:
        p = doc.add_paragraph()
        r = p.add_run("ไม่พบรูปภาพโครงสร้างชั้นทางในไฟล์ที่อัปโหลด")
        set_thai_font(r, size=14); r.font.italic = True
        return

    # ตาราง 2 คอลัมน์  (A4 content = 16 cm)
    DXA = 567   # 1 cm ≈ 567 DXA
    col = 8 * DXA
    total = col * 2
    fig = start_fig

    for i in range(0, len(summary_items), 2):
        pair = summary_items[i:i+2]
        tbl = doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_props(tbl, total, [col, col])

        for ci, cell in enumerate(tbl.rows[0].cells):
            set_cell_format(cell, col)
            cell.paragraphs[0].clear()
            if ci < len(pair):
                img_b, caption = pair[ci]
                _insert_image_cell(cell, img_b)
                cp = cell.add_paragraph()
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = cp.add_run(f"รูปที่ 2-{fig}  {caption}")
                set_thai_font(cr, size=13); cr.font.italic = True
                fig += 1
        doc.add_paragraph()


# ─────────────────────────────────────────────────────────────────────────────
# Master merge
# ─────────────────────────────────────────────────────────────────────────────

def merge_documents(uploaded_files, section_titles, project_name, report_date,
                    include_summary, summary_items, start_fig):
    """
    ลำดับ: ปก → สารบัญ → เนื้อหา → หน้าสรุป (ท้ายสุด)
    summary_items: list of (img_bytes, caption) ที่ผ่านการเลือกแล้ว
    """
    merged = Document()
    set_page_margins(merged.sections[0])

    # ══ ปก ═══════════════════════════════════════════════════════════════
    for _ in range(5): merged.add_paragraph()
    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("รายงานการออกแบบโครงสร้างชั้นทาง")
    set_thai_font(r, size=24); r.font.bold = True
    if project_name:
        p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(project_name); set_thai_font(r, size=20); r.font.bold = True
    for _ in range(4): merged.add_paragraph()
    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(report_date); set_thai_font(r, size=16)
    merged.add_page_break()

    # ══ สารบัญ ════════════════════════════════════════════════════════════
    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("สารบัญ"); set_thai_font(r, size=18); r.font.bold = True
    merged.add_paragraph()
    sec = 1
    for key, file in uploaded_files.items():
        if file is not None:
            p = merged.add_paragraph()
            r = p.add_run(f"{sec}. {section_titles[key]}")
            set_thai_font(r, size=15); sec += 1
    if include_summary and summary_items:
        p = merged.add_paragraph()
        r = p.add_run(f"{sec}. สรุปโครงสร้างชั้นทางที่ออกแบบด้วยวิธี AASHTO 1993")
        set_thai_font(r, size=15)
    merged.add_page_break()

    # ══ เนื้อหา ════════════════════════════════════════════════════════════
    sec = 1
    for key, file in uploaded_files.items():
        if file is None: continue
        fb = file.read(); file.seek(0)
        p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(f"{sec}. {section_titles[key]}")
        set_thai_font(r, size=18); r.font.bold = True
        merged.add_paragraph()
        append_document(merged, Document(io.BytesIO(fb)))
        merged.add_page_break()
        sec += 1

    # ══ หน้าสรุป (ท้ายสุด) ═══════════════════════════════════════════════
    if include_summary and summary_items:
        add_pavement_summary_page(merged, summary_items, start_fig=start_fig)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# UI Helper: Image Selector widget
# ─────────────────────────────────────────────────────────────────────────────

def image_selector_widget(file_obj, label, session_key):
    """
    แสดง thumbnail ของรูปทั้งหมดในไฟล์ และให้ user เลือก index
    Returns: img_bytes ของรูปที่เลือก หรือ None
    """
    if file_obj is None:
        st.caption("ยังไม่ได้อัปโหลดไฟล์")
        return None

    try:
        fb = file_obj.read(); file_obj.seek(0)
        images = extract_all_raster_images(fb)
    except Exception as e:
        st.error(f"อ่านไฟล์ไม่ได้: {e}")
        return None

    if not images:
        st.warning("⚠️ ไม่พบรูปภาพ raster (PNG/JPG) ในไฟล์นี้")
        st.caption("หมายเหตุ: รูปแบบ WMF/EMF ไม่รองรับ — กรุณาบันทึกรูปโครงสร้างชั้นทางเป็น PNG หรือ JPG")
        return None

    # แนะนำ index ที่น่าจะถูก
    suggested = suggest_crosssection_index(images)
    saved_idx = st.session_state.get(session_key, suggested)
    # ตรวจว่า saved index ยังใช้ได้
    if saved_idx >= len(images):
        saved_idx = suggested

    st.markdown(f'<div class="preview-box">', unsafe_allow_html=True)
    st.markdown(f"**{label}** — พบ {len(images)} รูป | แนะนำ: รูปที่ {suggested+1}")

    # แสดง thumbnails ทุกรูป
    cols_per_row = min(len(images), 4)
    rows = [images[i:i+cols_per_row] for i in range(0, len(images), cols_per_row)]

    selected_idx = saved_idx
    for row_imgs in rows:
        thumb_cols = st.columns(cols_per_row)
        for ci, img_info in enumerate(row_imgs):
            real_idx = images.index(img_info)
            with thumb_cols[ci]:
                is_selected = (real_idx == selected_idx)
                border_color = "#38A169" if is_selected else "#CBD5E0"
                st.markdown(
                    f'<div style="border:3px solid {border_color};border-radius:6px;padding:4px;'
                    f'background:{"#F0FFF4" if is_selected else "white"}">',
                    unsafe_allow_html=True
                )
                # thumbnail
                try:
                    thumb_bytes = _img_to_streamlit_bytes(img_info['bytes'], img_info['ext'])
                    st.image(thumb_bytes, use_container_width=True)
                except Exception:
                    st.write("[แสดงรูปไม่ได้]")

                dim_str = f"{img_info['width']}×{img_info['height']}" if img_info['width'] else "?"
                ratio_str = f"{img_info['aspect']:.2f}" if img_info['aspect'] else "?"
                st.caption(
                    f"รูปที่ {real_idx+1} | {dim_str}px\n"
                    f"ratio {ratio_str} | {img_info['size_kb']} KB"
                )
                if st.button(
                    "✅ เลือกรูปนี้" if is_selected else "เลือก",
                    key=f"{session_key}_btn_{real_idx}",
                    type="primary" if is_selected else "secondary"
                ):
                    selected_idx = real_idx
                    st.session_state[session_key] = real_idx
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.session_state[session_key] = selected_idx
    chosen = images[selected_idx]
    st.success(
        f"✅ เลือกรูปที่ {selected_idx+1}: {chosen['filename']} "
        f"({chosen['width']}×{chosen['height']}px, ratio={chosen['aspect']:.2f})"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return chosen['bytes']


# ─────────────────────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger v2.4</div>',
                unsafe_allow_html=True)

    # ── ข้อมูลโครงการ ─────────────────────────────────────────────────────
    st.markdown("### 📋 ข้อมูลโครงการ")
    c1, c2 = st.columns(2)
    with c1:
        project_name = st.text_input("ชื่อโครงการ", placeholder="กรอกชื่อโครงการ")
    with c2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")
    st.markdown("---")

    # ── ตั้งค่าหน้าสรุป ────────────────────────────────────────────────────
    st.markdown("### 📸 ตั้งค่าหน้าสรุปโครงสร้างชั้นทาง")
    c1, c2 = st.columns([1, 2])
    with c1:
        include_summary = st.checkbox("✅ เพิ่มหน้าสรุปโครงสร้างชั้นทาง", value=True)
    with c2:
        if include_summary:
            st.info("📋 4 รูปแบบ: AC / JPCP / JRCP (รูปเดียวกับ JPCP) / CRCP  |  📍 ท้ายสุดของรายงาน")

    summary_captions = {
        'ac':   'โครงสร้างชั้นทางรูปแบบที่ 1 ผิวทางลาดยาง แบบ AC',
        'jpcp': 'โครงสร้างชั้นทางรูปแบบที่ 2 ผิวทางคอนกรีต แบบ JPCP',
        'jrcp': 'โครงสร้างชั้นทางรูปแบบที่ 3 ผิวทางคอนกรีต แบบ JRCP',
        'crcp': 'โครงสร้างชั้นทางรูปแบบที่ 4 ผิวทางคอนกรีต แบบ CRCP',
    }
    start_fig = 11

    if include_summary:
        with st.expander("⚙️ ปรับ Caption และหมายเลขรูป"):
            c1, c2 = st.columns(2)
            with c1:
                start_fig = st.number_input("หมายเลขรูปเริ่มต้น (รูปที่ 2-?)",
                                            min_value=1, max_value=99, value=11)
                summary_captions['ac']   = st.text_input("Caption รูปแบบที่ 1 (AC)",   value=summary_captions['ac'])
                summary_captions['jpcp'] = st.text_input("Caption รูปแบบที่ 2 (JPCP)", value=summary_captions['jpcp'])
            with c2:
                summary_captions['jrcp'] = st.text_input("Caption รูปแบบที่ 3 (JRCP)", value=summary_captions['jrcp'])
                summary_captions['crcp'] = st.text_input("Caption รูปแบบที่ 4 (CRCP)",  value=summary_captions['crcp'])

    st.markdown("---")

    # ── Section titles ─────────────────────────────────────────────────────
    section_titles = {
        'truck_factor':      'การคำนวณ Truck Factor',
        'esals_ac':          'การคำนวณ ESALs สำหรับผิวทางลาดยาง (Flexible Pavement)',
        'esals_concrete':    'การคำนวณ ESALs สำหรับผิวทางคอนกรีต (Rigid Pavement)',
        'cbr_analysis':      'การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์',
        'ac_design':         'การออกแบบผิวทางลาดยาง (Flexible Pavement)',
        'jpcp_jrcp_design':  'การออกแบบผิวทางคอนกรีต JPCP/JRCP',
        'crcp_design':       'การออกแบบผิวทางคอนกรีต CRCP',
        'k_value_jpcp_jrcp': 'การคำนวณ Corrected Modulus of Subgrade Reaction (k-value) สำหรับ JPCP/JRCP',
        'k_value_crcp':      'การคำนวณ Corrected Modulus of Subgrade Reaction (k-value) สำหรับ CRCP',
        'cost_estimate':     'การประมาณราคาค่าก่อสร้าง',
    }

    # ── อัปโหลดไฟล์ ───────────────────────────────────────────────────────
    st.markdown("### 📁 อัปโหลดไฟล์รายงาน")
    st.info("💡 อัปโหลดไฟล์ Word (.docx)  ส่วนที่ไม่มีสามารถเว้นว่างได้")

    uploaded_files = {}

    st.markdown('<div class="section-header">📊 1. การคำนวณ Truck Factor</div>', unsafe_allow_html=True)
    uploaded_files['truck_factor'] = st.file_uploader("Truck Factor (ถ้ามี)", type=['docx'], key='ff_truck')

    st.markdown('<div class="section-header">📈 2. การคำนวณ ESALs</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: uploaded_files['esals_ac']       = st.file_uploader("2.1 ESALs Flexible", type=['docx'], key='ff_esals_ac')
    with c2: uploaded_files['esals_concrete'] = st.file_uploader("2.2 ESALs Rigid",    type=['docx'], key='ff_esals_con')

    st.markdown('<div class="section-header">🔬 3. การวิเคราะห์ค่า CBR</div>', unsafe_allow_html=True)
    uploaded_files['cbr_analysis'] = st.file_uploader("CBR Percentile", type=['docx'], key='ff_cbr')

    st.markdown('<div class="section-header">🛤️ 4. การออกแบบผิวทางลาดยาง (AC)</div>', unsafe_allow_html=True)
    uploaded_files['ac_design'] = st.file_uploader("AC Pavement Design", type=['docx'], key='ff_ac')

    st.markdown('<div class="section-header">🏗️ 5. การออกแบบผิวทางคอนกรีต</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: uploaded_files['jpcp_jrcp_design'] = st.file_uploader("5.1 JPCP/JRCP Design", type=['docx'], key='ff_jpcp')
    with c2: uploaded_files['crcp_design']       = st.file_uploader("5.2 CRCP Design",      type=['docx'], key='ff_crcp')

    st.markdown('<div class="section-header">📐 6. Corrected k-value</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: uploaded_files['k_value_jpcp_jrcp'] = st.file_uploader("6.1 k-value JPCP/JRCP", type=['docx'], key='ff_kv_jpcp')
    with c2: uploaded_files['k_value_crcp']       = st.file_uploader("6.2 k-value CRCP",      type=['docx'], key='ff_kv_crcp')

    st.markdown('<div class="section-header">💰 7. การประมาณราคาค่าก่อสร้าง</div>', unsafe_allow_html=True)
    uploaded_files['cost_estimate'] = st.file_uploader("ประมาณราคา (ถ้ามี)", type=['docx'], key='ff_cost')

    st.markdown("---")

    # ── เลือกรูปสำหรับหน้าสรุป ────────────────────────────────────────────
    ac_img_bytes = jpcp_img_bytes = crcp_img_bytes = None

    if include_summary:
        st.markdown("### 🖼️ เลือกรูปโครงสร้างชั้นทางสำหรับหน้าสรุป")
        st.info(
            "💡 **วิธีใช้**: โปรแกรมจะแสดงรูปภาพทั้งหมดในไฟล์ให้เลือก\n\n"
            "รูปโครงสร้างชั้นทางมักอยู่**ท้ายสุด**ของแต่ละไฟล์ (กรอบเขียวแสดงรูปที่แนะนำ)"
        )

        with st.expander("🛤️ เลือกรูป AC Design (รูปแบบที่ 1)", expanded=True):
            ac_img_bytes = image_selector_widget(
                uploaded_files.get('ac_design'),
                "AC Pavement Design", "sel_ac"
            )

        with st.expander("🏗️ เลือกรูป JPCP/JRCP Design (รูปแบบที่ 2 และ 3)", expanded=True):
            jpcp_img_bytes = image_selector_widget(
                uploaded_files.get('jpcp_jrcp_design'),
                "JPCP/JRCP Design (ใช้รูปเดียวกันสำหรับทั้ง JPCP และ JRCP)", "sel_jpcp"
            )

        with st.expander("🏗️ เลือกรูป CRCP Design (รูปแบบที่ 4)", expanded=True):
            crcp_img_bytes = image_selector_widget(
                uploaded_files.get('crcp_design'),
                "CRCP Design", "sel_crcp"
            )

    # ── สรุป summary items ─────────────────────────────────────────────────
    summary_items = []
    if include_summary:
        if ac_img_bytes:
            summary_items.append((ac_img_bytes,   summary_captions['ac']))
        if jpcp_img_bytes:
            summary_items.append((jpcp_img_bytes, summary_captions['jpcp']))
            summary_items.append((jpcp_img_bytes, summary_captions['jrcp']))  # JRCP ใช้รูปเดียวกัน
        if crcp_img_bytes:
            summary_items.append((crcp_img_bytes, summary_captions['crcp']))

    st.markdown("---")

    # ── สถานะไฟล์ ──────────────────────────────────────────────────────────
    st.markdown("### 📊 สถานะ")
    file_count = sum(1 for f in uploaded_files.values() if f is not None)

    labels = [
        ('truck_factor',      '1. Truck Factor'),
        ('esals_ac',          '2.1 ESALs Flex'),
        ('esals_concrete',    '2.2 ESALs Rigid'),
        ('cbr_analysis',      '3. CBR'),
        ('ac_design',         '4. AC Design ⭐'),
        ('jpcp_jrcp_design',  '5.1 JPCP/JRCP ⭐'),
        ('crcp_design',       '5.2 CRCP ⭐'),
        ('k_value_jpcp_jrcp', '6.1 k-val JPCP'),
        ('k_value_crcp',      '6.2 k-val CRCP'),
        ('cost_estimate',     '7. Cost'),
    ]
    cols = st.columns(5)
    for i, (key, name) in enumerate(labels):
        with cols[i % 5]:
            if uploaded_files.get(key):
                st.success(f"{name} ✅")
            else:
                st.warning(f"{name} ⬜")

    if include_summary:
        st.markdown(f"🖼️ รูปสรุปที่เลือก: **{len(summary_items)} รูปแบบ** "
                    f"({'AC ✅' if ac_img_bytes else 'AC ❌'} | "
                    f"{'JPCP ✅' if jpcp_img_bytes else 'JPCP ❌'} | "
                    f"{'CRCP ✅' if crcp_img_bytes else 'CRCP ❌'})")

    st.markdown(f"**อัปโหลด {file_count}/10 ไฟล์**")
    st.markdown("---")

    # ── รวมไฟล์ ────────────────────────────────────────────────────────────
    _, c2, _ = st.columns([1, 2, 1])
    with c2:
        merge_btn = st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True)

    if merge_btn:
        if file_count == 0:
            st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            with st.spinner("กำลังรวมไฟล์..."):
                try:
                    merged = merge_documents(
                        uploaded_files, section_titles,
                        project_name, report_date_str,
                        include_summary=include_summary,
                        summary_items=summary_items,
                        start_fig=int(start_fig),
                    )
                    out = io.BytesIO()
                    merged.save(out); out.seek(0)

                    base = "รายงานออกแบบโครงสร้างชั้นทาง"
                    if project_name:
                        base = f"รายงานออกแบบ_{project_name.replace(' ','_')}"

                    st.success(f"✅ เรียบร้อย! ({file_count} ไฟล์)")
                    if include_summary and summary_items:
                        st.info(f"🖼️ หน้าสรุป: {len(summary_items)} รูปแบบ (ท้ายสุดของรายงาน)")

                    st.markdown("### 📥 ดาวน์โหลด")
                    st.download_button(
                        "📄 ดาวน์โหลด Word (.docx)",
                        data=out.getvalue(),
                        file_name=f"{base}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"❌ {e}"); st.exception(e)

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#718096;font-size:14px;">
        <p>พัฒนาโดย ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม</p>
        <p>มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ</p>
        <p>© 2025 - Pavement Design Report Merger v2.4</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
