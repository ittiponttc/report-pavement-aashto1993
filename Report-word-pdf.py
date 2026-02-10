# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 2.3

โดย: ภาควิชาครุศาสตร์โยธา มจพ.

การปรับปรุง v2.3:
- แก้ไขปัญหารูปภาพไม่แสดง (rId remapping เมื่อ merge documents)
- ย้ายหน้าสรุปโครงสร้างชั้นทางไปอยู่ท้ายสุดของรายงาน
- เพิ่มรูปแบบที่ 3 (JRCP) ใช้รูปเดียวกับ JPCP → แสดง 4 รูปแบบ
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
import io
import zipfile

# ─────────────────────────────────────────────────────────────────────────────
# Page Config & CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide"
)
st.markdown("""
<style>
    .main-header {
        font-size:28px; font-weight:bold; text-align:center; padding:20px;
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
        color:white; border-radius:10px; margin-bottom:20px;
    }
    .sub-header { font-size:18px; color:#4A5568; text-align:center; margin-bottom:30px; }
    .section-header {
        background-color:#C6F6D5; padding:10px 15px; border-radius:8px;
        margin:15px 0 10px 0; font-weight:bold; color:#276749;
        border-left:4px solid #38A169;
    }
    .stButton>button {
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
        color:white; font-weight:bold; padding:10px 30px;
        border-radius:25px; border:none; font-size:16px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Word / Formatting Helpers
# ─────────────────────────────────────────────────────────────────────────────

def set_thai_font(run, font_name="TH Sarabun New", font_size=15):
    run.font.name = font_name
    run.font.size = Pt(font_size)
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rFonts.set(qn(attr), font_name)


def set_page_margins(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.orientation = WD_ORIENT.PORTRAIT
    for attr in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(section, attr, Cm(2.5))
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)


def set_cell_borders(cell, color="AAAAAA", size=4):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(size))
        el.set(qn('w:color'), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def set_cell_width(cell, width_dxa):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcW = OxmlElement('w:tcW')
    tcW.set(qn('w:w'), str(width_dxa))
    tcW.set(qn('w:type'), 'dxa')
    tcPr.append(tcW)


def set_cell_vAlign(cell, val='top'):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    vAlign = OxmlElement('w:vAlign')
    vAlign.set(qn('w:val'), val)
    tcPr.append(vAlign)


def set_cell_margin(cell, top=80, bottom=80, left=80, right=80):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for side, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:w'), str(val))
        el.set(qn('w:type'), 'dxa')
        tcMar.append(el)
    tcPr.append(tcMar)


def set_table_width(tbl, total_dxa, col_widths_dxa):
    tbl_el = tbl._tbl
    tblPr = tbl_el.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl_el.insert(0, tblPr)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), str(total_dxa))
    tblW.set(qn('w:type'), 'dxa')
    tblPr.append(tblW)
    tblGrid = OxmlElement('w:tblGrid')
    for w in col_widths_dxa:
        gridCol = OxmlElement('w:gridCol')
        gridCol.set(qn('w:w'), str(w))
        tblGrid.append(gridCol)
    tbl_el.insert(1, tblGrid)


# ─────────────────────────────────────────────────────────────────────────────
# Image Extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_raster_images_from_docx(file_bytes):
    """
    ดึงเฉพาะรูป raster (png/jpg/jpeg/gif/bmp/tiff) จาก docx
    กรอง wmf/emf ออก เพราะ python-docx add_picture ไม่รองรับ
    Returns: list of (img_bytes, ext) เรียงตามชื่อไฟล์
    """
    images = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as z:
            media_files = sorted(
                f for f in z.namelist() if f.startswith('word/media/')
            )
            for mf in media_files:
                ext = mf.rsplit('.', 1)[-1].lower() if '.' in mf else ''
                if ext in ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif'):
                    images.append((z.read(mf), ext))
    except Exception:
        pass
    return images


def get_best_image(file_bytes):
    """
    คืนรูปภาพที่ใหญ่สุด (bytes) จากไฟล์ docx
    หรือ None ถ้าไม่มีรูป raster เลย
    """
    imgs = extract_raster_images_from_docx(file_bytes)
    return max(imgs, key=lambda x: len(x[0])) if imgs else None


# ─────────────────────────────────────────────────────────────────────────────
# Document Merge — Fixed rId Remapping
# ─────────────────────────────────────────────────────────────────────────────

def append_document(master_doc, source_doc):
    """
    คัดลอกเนื้อหาจาก source_doc → master_doc
    แก้ปัญหารูปไม่แสดง: remap rId ในภาพก่อน append XML

    สาเหตุปัญหาเดิม:
      - source_doc มี rId1 → image.png
      - master_doc มี rId1 → styles (ซ้อนทับ)
      - deepcopy element คง rId1 เดิมไว้ → Word หา image ไม่เจอ
    แก้ไข:
      - relate_to() คืน new_rId ใน master_doc
      - แทนที่ r:embed/r:id ใน XML string ก่อน parse กลับ
    """
    # สร้าง mapping: old_rId → new_rId สำหรับรูปภาพทุกรูปใน source
    rId_map = {}
    for rel_id, rel in source_doc.part.rels.items():
        if "image" in rel.reltype:
            try:
                new_rId = master_doc.part.relate_to(rel.target_part, rel.reltype)
                rId_map[rel_id] = new_rId
            except Exception:
                pass

    # คัดลอก body elements พร้อม remap
    for element in source_doc.element.body:
        if element.tag.endswith('sectPr'):
            continue

        new_element = deepcopy(element)

        if rId_map:
            xml_str = etree.tostring(new_element, encoding='unicode')
            for old_id, new_id in rId_map.items():
                xml_str = xml_str.replace(f'r:embed="{old_id}"', f'r:embed="{new_id}"')
                xml_str = xml_str.replace(f'r:id="{old_id}"',    f'r:id="{new_id}"')
                xml_str = xml_str.replace(f'r:link="{old_id}"',  f'r:link="{new_id}"')
            try:
                new_element = etree.fromstring(xml_str)
            except Exception:
                pass  # fallback ใช้ deepcopy เดิม

        master_doc.element.body.append(new_element)


# ─────────────────────────────────────────────────────────────────────────────
# Summary Page — 4 รูปแบบ, ท้ายสุด
# ─────────────────────────────────────────────────────────────────────────────

def _add_image_in_cell(cell, img_bytes):
    """ใส่รูปลงใน cell ด้วยขนาดที่ลดหลั่น; คืน True ถ้าสำเร็จ"""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for w_cm in (7.0, 6.0, 5.5):
        try:
            run = para.add_run()
            run.add_picture(io.BytesIO(img_bytes), width=Cm(w_cm))
            return True
        except Exception:
            # ลบ run ที่ fail แล้วลองขนาดเล็กลง
            try:
                p_xml = para._p
                for r in p_xml.findall(qn('w:r')):
                    p_xml.remove(r)
            except Exception:
                pass
    # placeholder
    r = para.add_run("[ไม่สามารถแสดงรูปภาพได้]")
    set_thai_font(r, font_size=12)
    r.font.italic = True
    return False


def add_pavement_summary_page(doc, summary_items, start_fig_num=11):
    """
    เพิ่มหน้าสรุปโครงสร้างชั้นทาง (ท้ายสุด)
    summary_items: list of (img_bytes, caption_str)
    แสดงในตาราง 2 คอลัมน์
    """
    # หัวข้อ
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("สรุปโครงสร้างชั้นทางที่ออกแบบด้วยวิธี AASHTO 1993")
    set_thai_font(r, font_size=18); r.font.bold = True

    # คำอธิบาย
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    n = len(summary_items)
    r = p.add_run(
        "จากการคำนวณ/ออกแบบตามวิธี AASHTO 1993 สำหรับการออกแบบโครงสร้างชั้นทาง"
        " (Asphalt Concrete) และผิวทางคอนกรีต (Concrete Pavement)"
        " สามารถสรุปรูปแบบโครงสร้างชั้นทาง ดังแสดงในรูปที่ 2-{} ถึง รูปที่ 2-{}".format(
            start_fig_num, start_fig_num + n - 1)
    )
    set_thai_font(r, font_size=15)
    doc.add_paragraph()

    if not summary_items:
        p = doc.add_paragraph()
        r = p.add_run("ไม่พบรูปภาพโครงสร้างชั้นทางในไฟล์ที่อัปโหลด")
        set_thai_font(r, font_size=14); r.font.italic = True
        return

    # ตาราง 2 คอลัมน์  (A4 content = 16 cm → 8 cm ต่อคอลัมน์)
    CM_DXA = 567          # 1 cm ≈ 567 DXA
    col_dxa = 8 * CM_DXA  # 4536
    total_dxa = col_dxa * 2

    fig = start_fig_num
    for i in range(0, len(summary_items), 2):
        pair = summary_items[i:i + 2]

        tbl = doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_width(tbl, total_dxa, [col_dxa, col_dxa])

        for col_idx, cell in enumerate(tbl.rows[0].cells):
            set_cell_width(cell, col_dxa)
            set_cell_borders(cell, color="AAAAAA", size=4)
            set_cell_vAlign(cell, 'top')
            set_cell_margin(cell, top=80, bottom=80, left=80, right=80)
            cell.paragraphs[0].clear()

            if col_idx < len(pair):
                img_bytes, caption = pair[col_idx]
                _add_image_in_cell(cell, img_bytes)
                # Caption
                p = cell.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(f"รูปที่ 2-{fig}  {caption}")
                set_thai_font(r, font_size=13); r.font.italic = True
                fig += 1

        doc.add_paragraph()  # ระยะห่างระหว่างแถว


# ─────────────────────────────────────────────────────────────────────────────
# Collect Summary Images (4 รูปแบบ)
# ─────────────────────────────────────────────────────────────────────────────

def collect_summary_images(uploaded_files, captions):
    """
    สร้าง list รูปสรุป 4 รูปแบบ:
      1. AC Design
      2. JPCP  (จากไฟล์ jpcp_jrcp_design)
      3. JRCP  (รูปเดียวกับ JPCP แต่ caption ต่างกัน)
      4. CRCP
    คืน list of (img_bytes, caption)
    """
    items = []

    def _pull(key, cap_key, default_cap):
        f = uploaded_files.get(key)
        if f is None:
            return None
        try:
            fb = f.read(); f.seek(0)
            img = get_best_image(fb)
            if img:
                return (img[0], captions.get(cap_key, default_cap))
        except Exception:
            pass
        return None

    # รูปแบบที่ 1 – AC
    r = _pull('ac_design', 'ac_design',
              'โครงสร้างชั้นทางรูปแบบที่ 1 ผิวทางลาดยาง แบบ AC')
    if r:
        items.append(r)

    # รูปแบบที่ 2 – JPCP
    r = _pull('jpcp_jrcp_design', 'jpcp_design',
              'โครงสร้างชั้นทางรูปแบบที่ 2 ผิวทางคอนกรีต แบบ JPCP')
    jpcp_bytes = r[0] if r else None
    if r:
        items.append(r)

    # รูปแบบที่ 3 – JRCP (รูปเดียวกับ JPCP)
    if jpcp_bytes is not None:
        items.append((
            jpcp_bytes,
            captions.get('jrcp_design',
                         'โครงสร้างชั้นทางรูปแบบที่ 3 ผิวทางคอนกรีต แบบ JRCP')
        ))

    # รูปแบบที่ 4 – CRCP
    r = _pull('crcp_design', 'crcp_design',
              'โครงสร้างชั้นทางรูปแบบที่ 4 ผิวทางคอนกรีต แบบ CRCP')
    if r:
        items.append(r)

    return items


# ─────────────────────────────────────────────────────────────────────────────
# Master Merge
# ─────────────────────────────────────────────────────────────────────────────

def merge_documents(uploaded_files, section_titles, project_name, report_date,
                    include_summary=True, summary_captions=None, start_fig_num=11):
    """
    ลำดับเอกสาร:
      1. หน้าปก
      2. สารบัญ
      3. เนื้อหาแต่ละส่วน (พร้อมรูปภาพถูกต้อง)
      4. หน้าสรุปโครงสร้างชั้นทาง ← ท้ายสุด
    """
    if summary_captions is None:
        summary_captions = {}

    # ดึงรูปสรุปก่อน (ก่อนที่ file pointer จะถูกใช้ใน merge loop)
    summary_items = []
    if include_summary:
        summary_items = collect_summary_images(uploaded_files, summary_captions)

    # ── สร้างเอกสารหลัก ──────────────────────────────────────────────────
    merged = Document()
    set_page_margins(merged.sections[0])

    # ══ 1. หน้าปก ════════════════════════════════════════════════════════
    for _ in range(5):
        merged.add_paragraph()

    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("รายงานการออกแบบโครงสร้างชั้นทาง")
    set_thai_font(r, font_size=24); r.font.bold = True

    if project_name:
        p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(project_name)
        set_thai_font(r, font_size=20); r.font.bold = True

    for _ in range(4):
        merged.add_paragraph()

    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(report_date)
    set_thai_font(r, font_size=16)

    merged.add_page_break()

    # ══ 2. สารบัญ ════════════════════════════════════════════════════════
    p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("สารบัญ"); set_thai_font(r, font_size=18); r.font.bold = True
    merged.add_paragraph()

    sec = 1
    for key, file in uploaded_files.items():
        if file is not None:
            p = merged.add_paragraph()
            r = p.add_run(f"{sec}. {section_titles[key]}")
            set_thai_font(r, font_size=15)
            sec += 1

    if include_summary and summary_items:
        p = merged.add_paragraph()
        r = p.add_run(f"{sec}. สรุปโครงสร้างชั้นทางที่ออกแบบด้วยวิธี AASHTO 1993")
        set_thai_font(r, font_size=15)

    merged.add_page_break()

    # ══ 3. เนื้อหา ═══════════════════════════════════════════════════════
    sec = 1
    for key, file in uploaded_files.items():
        if file is None:
            continue
        fb = file.read(); file.seek(0)

        p = merged.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(f"{sec}. {section_titles[key]}")
        set_thai_font(r, font_size=18); r.font.bold = True
        merged.add_paragraph()

        append_document(merged, Document(io.BytesIO(fb)))
        merged.add_page_break()
        sec += 1

    # ══ 4. หน้าสรุป (ท้ายสุด) ════════════════════════════════════════════
    if include_summary and summary_items:
        add_pavement_summary_page(merged, summary_items, start_fig_num=start_fig_num)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger v2.3</div>',
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
        include_summary = st.checkbox(
            "✅ เพิ่มหน้าสรุปโครงสร้างชั้นทาง",
            value=True,
            help="แสดง 4 รูปแบบ ที่ท้ายสุดของรายงาน"
        )
    with c2:
        if include_summary:
            st.info(
                "📋 **4 รูปแบบ** : AC → JPCP → JRCP (รูปเดียวกับ JPCP) → CRCP\n\n"
                "📍 **ตำแหน่ง** : ท้ายสุดของรายงาน (หลังเนื้อหาทุกส่วน)"
            )

    summary_captions = {
        'ac_design':   'โครงสร้างชั้นทางรูปแบบที่ 1 ผิวทางลาดยาง แบบ AC',
        'jpcp_design': 'โครงสร้างชั้นทางรูปแบบที่ 2 ผิวทางคอนกรีต แบบ JPCP',
        'jrcp_design': 'โครงสร้างชั้นทางรูปแบบที่ 3 ผิวทางคอนกรีต แบบ JRCP',
        'crcp_design': 'โครงสร้างชั้นทางรูปแบบที่ 4 ผิวทางคอนกรีต แบบ CRCP',
    }
    start_fig_num = 11

    if include_summary:
        with st.expander("⚙️ ปรับแต่ง Caption และหมายเลขรูป"):
            c1, c2 = st.columns(2)
            with c1:
                start_fig_num = st.number_input(
                    "หมายเลขรูปเริ่มต้น (รูปที่ 2-?)",
                    min_value=1, max_value=99, value=11, step=1)
                summary_captions['ac_design'] = st.text_input(
                    "Caption รูปแบบที่ 1 (AC)",
                    value=summary_captions['ac_design'])
                summary_captions['jpcp_design'] = st.text_input(
                    "Caption รูปแบบที่ 2 (JPCP)",
                    value=summary_captions['jpcp_design'])
            with c2:
                summary_captions['jrcp_design'] = st.text_input(
                    "Caption รูปแบบที่ 3 (JRCP)",
                    value=summary_captions['jrcp_design'])
                summary_captions['crcp_design'] = st.text_input(
                    "Caption รูปแบบที่ 4 (CRCP)",
                    value=summary_captions['crcp_design'])

    st.markdown("---")

    # ── Section Titles ─────────────────────────────────────────────────────
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
    st.info("💡 อัปโหลดไฟล์ Word (.docx) สำหรับแต่ละส่วน  ส่วนที่ไม่มีสามารถเว้นว่างได้")

    uploaded_files = {}

    # 1. Truck Factor
    st.markdown('<div class="section-header">📊 1. การคำนวณ Truck Factor</div>', unsafe_allow_html=True)
    uploaded_files['truck_factor'] = st.file_uploader(
        "Truck Factor (ถ้ามี)", type=['docx'], key='truck_factor')

    # 2. ESALs
    st.markdown('<div class="section-header">📈 2. การคำนวณ ESALs</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        uploaded_files['esals_ac'] = st.file_uploader(
            "2.1 ESALs ผิวทางลาดยาง (Flexible)", type=['docx'], key='esals_ac')
    with c2:
        uploaded_files['esals_concrete'] = st.file_uploader(
            "2.2 ESALs ผิวทางคอนกรีต (Rigid)", type=['docx'], key='esals_concrete')

    # 3. CBR
    st.markdown('<div class="section-header">🔬 3. การวิเคราะห์ค่า CBR</div>', unsafe_allow_html=True)
    uploaded_files['cbr_analysis'] = st.file_uploader(
        "CBR Percentile Analysis", type=['docx'], key='cbr_analysis')

    # 4. AC Design
    st.markdown('<div class="section-header">🛤️ 4. การออกแบบผิวทางลาดยาง (AC)</div>',
                unsafe_allow_html=True)
    if include_summary:
        st.caption("🖼️ รูปจากไฟล์นี้ = รูปแบบที่ 1 ในหน้าสรุป")
    uploaded_files['ac_design'] = st.file_uploader(
        "AC Pavement Design", type=['docx'], key='ac_design')

    # 5. Rigid
    st.markdown('<div class="section-header">🏗️ 5. การออกแบบผิวทางคอนกรีต</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if include_summary:
            st.caption("🖼️ รูปจากไฟล์นี้ = รูปแบบที่ 2 (JPCP) และ 3 (JRCP)")
        uploaded_files['jpcp_jrcp_design'] = st.file_uploader(
            "5.1 JPCP/JRCP Design", type=['docx'], key='jpcp_jrcp_design')
    with c2:
        if include_summary:
            st.caption("🖼️ รูปจากไฟล์นี้ = รูปแบบที่ 4 (CRCP)")
        uploaded_files['crcp_design'] = st.file_uploader(
            "5.2 CRCP Design", type=['docx'], key='crcp_design')

    # 6. k-value
    st.markdown('<div class="section-header">📐 6. Corrected k-value</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        uploaded_files['k_value_jpcp_jrcp'] = st.file_uploader(
            "6.1 k-value JPCP/JRCP", type=['docx'], key='k_value_jpcp_jrcp')
    with c2:
        uploaded_files['k_value_crcp'] = st.file_uploader(
            "6.2 k-value CRCP", type=['docx'], key='k_value_crcp')

    # 7. Cost
    st.markdown('<div class="section-header">💰 7. การประมาณราคาค่าก่อสร้าง</div>',
                unsafe_allow_html=True)
    uploaded_files['cost_estimate'] = st.file_uploader(
        "ประมาณราคา (ถ้ามี)", type=['docx'], key='cost_estimate')

    st.markdown("---")

    # ── สถานะ ──────────────────────────────────────────────────────────────
    st.markdown("### 📊 สถานะไฟล์ที่อัปโหลด")
    file_count = sum(1 for f in uploaded_files.values() if f is not None)

    labels = [
        ('truck_factor',      '1. Truck Factor'),
        ('esals_ac',          '2.1 ESALs Flexible'),
        ('esals_concrete',    '2.2 ESALs Rigid'),
        ('cbr_analysis',      '3. CBR Analysis'),
        ('ac_design',         '4. AC Design ⭐'),
        ('jpcp_jrcp_design',  '5.1 JPCP/JRCP ⭐'),
        ('crcp_design',       '5.2 CRCP ⭐'),
        ('k_value_jpcp_jrcp', '6.1 k-value JPCP/JRCP'),
        ('k_value_crcp',      '6.2 k-value CRCP'),
        ('cost_estimate',     '7. Cost Estimate'),
    ]
    cols = st.columns(3)
    for i, (key, name) in enumerate(labels):
        with cols[i % 3]:
            if uploaded_files.get(key) is not None:
                st.success(f"{name}: ✅")
            else:
                st.warning(f"{name}: ⬜")

    if include_summary:
        st.caption("⭐ = ดึงรูปมาใช้ในหน้าสรุป (JPCP/JRCP → ใช้ได้ทั้ง JPCP และ JRCP)")
    st.markdown(f"**อัปโหลดแล้ว {file_count} / 10 ไฟล์**")
    st.markdown("---")

    # ── รวมไฟล์ ────────────────────────────────────────────────────────────
    _, c2, _ = st.columns([1, 2, 1])
    with c2:
        merge_btn = st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True)

    if merge_btn:
        if file_count == 0:
            st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            with st.spinner("กำลังรวมไฟล์และสร้างรายงาน..."):
                try:
                    merged = merge_documents(
                        uploaded_files, section_titles,
                        project_name, report_date_str,
                        include_summary=include_summary,
                        summary_captions=summary_captions,
                        start_fig_num=int(start_fig_num),
                    )
                    out = io.BytesIO()
                    merged.save(out); out.seek(0)

                    base = "รายงานออกแบบโครงสร้างชั้นทาง"
                    if project_name:
                        base = f"รายงานออกแบบ_{project_name.replace(' ', '_')}"

                    st.success(f"✅ รวมไฟล์เรียบร้อยแล้ว! ({file_count} ไฟล์)")

                    if include_summary:
                        n_imgs = len(collect_summary_images(uploaded_files, summary_captions))
                        if n_imgs > 0:
                            st.info(f"🖼️ หน้าสรุปโครงสร้างชั้นทาง: {n_imgs} รูปแบบ (ท้ายสุดของรายงาน)")
                        else:
                            st.warning("⚠️ ไม่พบรูป raster (PNG/JPG) ในไฟล์ออกแบบ — หน้าสรุปจะไม่มีรูปภาพ")

                    st.markdown("### 📥 ดาวน์โหลดรายงาน")
                    st.download_button(
                        label="📄 ดาวน์โหลดไฟล์ Word (.docx)",
                        data=out.getvalue(),
                        file_name=f"{base}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                    st.exception(e)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#718096;font-size:14px;">
        <p>พัฒนาโดย ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม</p>
        <p>มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ</p>
        <p>© 2025 - Pavement Design Report Merger v2.3</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
