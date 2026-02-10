# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 2.2 (Stable)

โดย: ภาควิชาครุศาสตร์โยธา มจพ.
"""

import streamlit as st
import os
import tempfile
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from copy import deepcopy
import io
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide"
)

# CSS สำหรับตกแต่งหน้าเว็บ
st.markdown("""
<style>
    .main-header {
        font-size: 28px;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 18px;
        color: #4A5568;
        text-align: center;
        margin-bottom: 30px;
    }
    .file-section {
        background-color: #F7FAFC;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
    }
    .section-header {
        background-color: #C6F6D5;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 15px 0 10px 0;
        font-weight: bold;
        color: #276749;
        border-left: 4px solid #38A169;
    }
    .success-box {
        background-color: #C6F6D5;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #38A169;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 10px 30px;
        border-radius: 25px;
        border: none;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)


def set_thai_font(run, font_name="TH Sarabun New", font_size=15):
    run.font.name = font_name
    run.font.size = Pt(font_size)
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)


def set_page_margins(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.orientation = WD_ORIENT.PORTRAIT
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)


# ===============================
# Version 2.2: เสถียรขึ้น
# ===============================
def append_document(master_doc, source_doc):
    """
    คัดลอกเนื้อหาจากเอกสารต้นทางไปยังเอกสารปลายทาง
    รองรับรูปภาพ ตาราง และการจัดรูปแบบ
    """

    # คัดลอก relationship ของรูปภาพ
    for rel in source_doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                image_part = rel.target_part
                master_doc.part.relate_to(image_part, rel.reltype)
            except:
                pass

    # คัดลอก element ใน body
    for element in source_doc.element.body:
        if element.tag.endswith('sectPr'):
            continue
        new_element = deepcopy(element)
        master_doc.element.body.append(new_element)


def merge_documents(uploaded_files, section_titles, project_name, report_date):

    merged_doc = Document()
    section = merged_doc.sections[0]
    set_page_margins(section)

    # หน้าปก
    main_title = merged_doc.add_paragraph()
    main_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    main_run = main_title.add_run("รายงานการออกแบบโครงสร้างชั้นทาง")
    set_thai_font(main_run, font_size=24)
    main_run.font.bold = True

    if project_name:
        project_para = merged_doc.add_paragraph()
        project_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        project_run = project_para.add_run(project_name)
        set_thai_font(project_run, font_size=20)
        project_run.font.bold = True

    date_para = merged_doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(report_date)
    set_thai_font(date_run, font_size=16)

    merged_doc.add_page_break()

    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            file_bytes = file.read()
            file.seek(0)

            # หัวข้อ
            section_title_para = merged_doc.add_paragraph()
            section_run = section_title_para.add_run(
                f"{section_num}. {section_titles[key]}"
            )
            set_thai_font(section_run, font_size=18)
            section_run.font.bold = True

            merged_doc.add_paragraph()

            source_doc = Document(io.BytesIO(file_bytes))
            append_document(merged_doc, source_doc)

            merged_doc.add_page_break()
            section_num += 1

    return merged_doc


# ===============================
# UI เดิมทั้งหมด (ไม่เปลี่ยน)
# ===============================
def main():

    st.markdown(
        '<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>',
        unsafe_allow_html=True
    )

    st.markdown("### 📋 ข้อมูลโครงการ")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการ")
    with col2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")

    section_titles = {
        'truck_factor': 'การคำนวณ Truck Factor',
        'esals_ac': 'การคำนวณ ESALs สำหรับผิวทางลาดยาง',
        'esals_concrete': 'การคำนวณ ESALs สำหรับผิวทางคอนกรีต',
        'cbr_analysis': 'การวิเคราะห์ค่า CBR',
        'ac_design': 'การออกแบบผิวทางลาดยาง',
        'jpcp_jrcp_design': 'การออกแบบ JPCP/JRCP',
        'crcp_design': 'การออกแบบ CRCP',
        'k_value_jpcp_jrcp': 'k-value สำหรับ JPCP/JRCP',
        'k_value_crcp': 'k-value สำหรับ CRCP',
        'cost_estimate': 'การประมาณราคา'
    }

    uploaded_files = {}
    for key in section_titles:
        uploaded_files[key] = st.file_uploader(
            section_titles[key],
            type=['docx'],
            key=key
        )

    merge_button = st.button("🔄 รวมไฟล์และสร้างรายงาน")

    if merge_button:
        file_count = sum(1 for f in uploaded_files.values() if f is not None)

        if file_count == 0:
            st.error("กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            merged_doc = merge_documents(
                uploaded_files,
                section_titles,
                project_name,
                report_date_str
            )

            output = io.BytesIO()
            merged_doc.save(output)
            output.seek(0)

            st.download_button(
                label="📄 ดาวน์โหลดรายงาน",
                data=output.getvalue(),
                file_name="merged_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )


if __name__ == "__main__":
    main()
