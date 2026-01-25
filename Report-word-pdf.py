# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 1.0

โดย: ภาควิชาครุศาสตร์โยธา มจพ.
"""

import streamlit as st
import os
import tempfile
import shutil
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import subprocess
import io
import zipfile

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
        margin-bottom: 15px;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background-color: #C6F6D5;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #38A169;
    }
    .warning-box {
        background-color: #FEFCBF;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #D69E2E;
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
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)


def set_thai_font(run, font_name="TH Sarabun New", font_size=15):
    """ตั้งค่าฟอนต์ไทยและขนาด"""
    run.font.name = font_name
    run.font.size = Pt(font_size)
    # ตั้งค่าฟอนต์สำหรับภาษาไทย
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)


def set_page_margins(section):
    """ตั้งค่าหน้ากระดาษ A4 แนวตั้ง กั้นหน้า-หลัง 2.5 cm"""
    section.page_width = Cm(21)  # A4 width
    section.page_height = Cm(29.7)  # A4 height
    section.orientation = WD_ORIENT.PORTRAIT
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)


def copy_paragraph(source_para, target_doc):
    """คัดลอก paragraph จากเอกสารต้นทางไปยังเอกสารปลายทาง"""
    new_para = target_doc.add_paragraph()
    
    # คัดลอก alignment
    new_para.alignment = source_para.alignment
    
    # คัดลอก paragraph format
    if source_para.paragraph_format.line_spacing:
        new_para.paragraph_format.line_spacing = source_para.paragraph_format.line_spacing
    if source_para.paragraph_format.space_before:
        new_para.paragraph_format.space_before = source_para.paragraph_format.space_before
    if source_para.paragraph_format.space_after:
        new_para.paragraph_format.space_after = source_para.paragraph_format.space_after
    if source_para.paragraph_format.first_line_indent:
        new_para.paragraph_format.first_line_indent = source_para.paragraph_format.first_line_indent
    
    # คัดลอก runs
    for run in source_para.runs:
        new_run = new_para.add_run(run.text)
        # คัดลอก format
        if run.font.bold:
            new_run.font.bold = run.font.bold
        if run.font.italic:
            new_run.font.italic = run.font.italic
        if run.font.underline:
            new_run.font.underline = run.font.underline
        if run.font.size:
            new_run.font.size = run.font.size
        if run.font.name:
            new_run.font.name = run.font.name
            # ตั้งค่าฟอนต์ไทย
            r = new_run._r
            rPr = r.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn('w:ascii'), run.font.name)
            rFonts.set(qn('w:hAnsi'), run.font.name)
            rFonts.set(qn('w:cs'), run.font.name)
        if run.font.color.rgb:
            new_run.font.color.rgb = run.font.color.rgb
    
    return new_para


def copy_table(source_table, target_doc):
    """คัดลอกตารางจากเอกสารต้นทางไปยังเอกสารปลายทาง"""
    # สร้างตารางใหม่
    rows = len(source_table.rows)
    cols = len(source_table.columns)
    new_table = target_doc.add_table(rows=rows, cols=cols)
    
    # คัดลอกข้อมูลในตาราง
    for i, row in enumerate(source_table.rows):
        for j, cell in enumerate(row.cells):
            new_cell = new_table.rows[i].cells[j]
            # คัดลอกข้อความ
            for para in cell.paragraphs:
                if para.text.strip():
                    new_para = new_cell.paragraphs[0] if new_cell.paragraphs else new_cell.add_paragraph()
                    new_para.clear()
                    for run in para.runs:
                        new_run = new_para.add_run(run.text)
                        if run.font.bold:
                            new_run.font.bold = run.font.bold
                        if run.font.size:
                            new_run.font.size = run.font.size
                        if run.font.name:
                            new_run.font.name = run.font.name
    
    return new_table


def extract_document_content(doc):
    """แยกเนื้อหาจากเอกสาร รวมถึงตาราง"""
    content = []
    for element in doc.element.body:
        if element.tag.endswith('p'):  # paragraph
            for para in doc.paragraphs:
                if para._element == element:
                    content.append(('paragraph', para))
                    break
        elif element.tag.endswith('tbl'):  # table
            for table in doc.tables:
                if table._element == element:
                    content.append(('table', table))
                    break
    return content


def merge_documents(uploaded_files, section_titles, project_name, report_date):
    """รวมเอกสารทั้งหมดเป็นไฟล์เดียว"""
    
    # สร้างเอกสารใหม่
    merged_doc = Document()
    
    # ตั้งค่าหน้ากระดาษ
    section = merged_doc.sections[0]
    set_page_margins(section)
    
    # สร้างหน้าปก
    title_para = merged_doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run("\n\n\n\n\n")
    
    # หัวข้อหลัก
    main_title = merged_doc.add_paragraph()
    main_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    main_run = main_title.add_run("รายงานการออกแบบโครงสร้างชั้นทาง")
    set_thai_font(main_run, font_size=24)
    main_run.font.bold = True
    
    # ชื่อโครงการ
    if project_name:
        project_para = merged_doc.add_paragraph()
        project_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        project_run = project_para.add_run(f"\n{project_name}")
        set_thai_font(project_run, font_size=20)
        project_run.font.bold = True
    
    # วันที่
    date_para = merged_doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(f"\n\n\n\n{report_date}")
    set_thai_font(date_run, font_size=16)
    
    # ขึ้นหน้าใหม่
    merged_doc.add_page_break()
    
    # สารบัญ
    toc_title = merged_doc.add_paragraph()
    toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    toc_run = toc_title.add_run("สารบัญ")
    set_thai_font(toc_run, font_size=18)
    toc_run.font.bold = True
    
    merged_doc.add_paragraph()  # เว้นบรรทัด
    
    # รายการสารบัญ
    toc_items = []
    for i, (key, file) in enumerate(uploaded_files.items()):
        if file is not None:
            toc_items.append(f"{i+1}. {section_titles[key]}")
    
    for item in toc_items:
        toc_para = merged_doc.add_paragraph()
        toc_run = toc_para.add_run(item)
        set_thai_font(toc_run, font_size=15)
    
    # ขึ้นหน้าใหม่
    merged_doc.add_page_break()
    
    # รวมเนื้อหาจากแต่ละไฟล์
    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            # อ่านไฟล์
            file_bytes = file.read()
            file.seek(0)  # reset file pointer
            
            # โหลดเอกสาร
            source_doc = Document(io.BytesIO(file_bytes))
            
            # หัวข้อส่วน
            section_title = merged_doc.add_paragraph()
            section_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
            section_run = section_title.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(section_run, font_size=18)
            section_run.font.bold = True
            
            merged_doc.add_paragraph()  # เว้นบรรทัด
            
            # คัดลอกเนื้อหา
            for para in source_doc.paragraphs:
                if para.text.strip():  # ข้ามย่อหน้าว่าง
                    new_para = merged_doc.add_paragraph()
                    new_para.alignment = para.alignment
                    
                    for run in para.runs:
                        new_run = new_para.add_run(run.text)
                        # รักษา format เดิม
                        if run.font.bold:
                            new_run.font.bold = run.font.bold
                        if run.font.italic:
                            new_run.font.italic = run.font.italic
                        if run.font.underline:
                            new_run.font.underline = run.font.underline
                        # ตั้งค่าฟอนต์
                        if run.font.size:
                            new_run.font.size = run.font.size
                        else:
                            new_run.font.size = Pt(15)
                        
                        font_name = run.font.name if run.font.name else "TH Sarabun New"
                        new_run.font.name = font_name
                        r = new_run._r
                        rPr = r.get_or_add_rPr()
                        rFonts = rPr.get_or_add_rFonts()
                        rFonts.set(qn('w:ascii'), font_name)
                        rFonts.set(qn('w:hAnsi'), font_name)
                        rFonts.set(qn('w:cs'), font_name)
            
            # คัดลอกตาราง
            for table in source_doc.tables:
                merged_doc.add_paragraph()  # เว้นก่อนตาราง
                copy_table(table, merged_doc)
                merged_doc.add_paragraph()  # เว้นหลังตาราง
            
            # ขึ้นหน้าใหม่สำหรับส่วนถัดไป
            merged_doc.add_page_break()
            section_num += 1
    
    return merged_doc


def convert_to_pdf(docx_path, output_path):
    """แปลงไฟล์ Word เป็น PDF โดยใช้ LibreOffice"""
    try:
        # ใช้ LibreOffice สำหรับแปลง
        cmd = [
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_path),
            docx_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # ตรวจสอบผลลัพธ์
        expected_pdf = os.path.splitext(docx_path)[0] + '.pdf'
        if os.path.exists(expected_pdf):
            if expected_pdf != output_path:
                shutil.move(expected_pdf, output_path)
            return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการแปลง PDF: {str(e)}")
        return False


def main():
    # หัวข้อหลัก
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger</div>', unsafe_allow_html=True)
    
    # ข้อมูลโครงการ
    st.markdown("### 📋 ข้อมูลโครงการ")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการ", placeholder="กรอกชื่อโครงการ")
    with col2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")
    
    st.markdown("---")
    
    # คำอธิบายส่วนต่างๆ
    section_titles = {
        'truck_factor': 'การคำนวณ Truck Factor',
        'esals': 'การคำนวณ ESALs (Equivalent Single Axle Loads)',
        'ac_design': 'การออกแบบผิวทางแอสฟัลต์ (AC)',
        'concrete_design': 'การออกแบบผิวทางคอนกรีต (JPCP)',
        'subgrade_modulus': 'การคำนวณ Corrected Modulus of Subgrade Reaction',
        'cost_estimate': 'การประมาณราคาค่าก่อสร้าง'
    }
    
    st.markdown("### 📁 อัปโหลดไฟล์รายงาน")
    st.info("💡 อัปโหลดไฟล์ Word (.docx) สำหรับแต่ละส่วนของรายงาน ไฟล์ที่มีเครื่องหมาย (ถ้ามี) สามารถเว้นว่างได้")
    
    uploaded_files = {}
    
    # ส่วนที่ 1: Truck Factor (ถ้ามี)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**1. การคำนวณ Truck Factor** (ถ้ามี)")
    uploaded_files['truck_factor'] = st.file_uploader(
        "เลือกไฟล์ Truck Factor",
        type=['docx'],
        key='truck_factor',
        help="ไฟล์รายงานการคำนวณ Truck Factor"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ส่วนที่ 2: ESALs
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**2. การคำนวณ ESALs** ⭐")
    uploaded_files['esals'] = st.file_uploader(
        "เลือกไฟล์ ESALs",
        type=['docx'],
        key='esals',
        help="ไฟล์รายงานการคำนวณ Equivalent Single Axle Loads"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ส่วนที่ 3: AC Design
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**3. การออกแบบผิวทาง AC** ⭐")
    uploaded_files['ac_design'] = st.file_uploader(
        "เลือกไฟล์ออกแบบ AC",
        type=['docx'],
        key='ac_design',
        help="ไฟล์รายงานการออกแบบผิวทางแอสฟัลต์"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ส่วนที่ 4: Concrete Design
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**4. การออกแบบผิวทางคอนกรีต (JPCP)** ⭐")
    uploaded_files['concrete_design'] = st.file_uploader(
        "เลือกไฟล์ออกแบบ JPCP",
        type=['docx'],
        key='concrete_design',
        help="ไฟล์รายงานการออกแบบผิวทาง Jointed Plain Concrete Pavement"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ส่วนที่ 5: Subgrade Modulus
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**5. Corrected Modulus of Subgrade Reaction** ⭐")
    uploaded_files['subgrade_modulus'] = st.file_uploader(
        "เลือกไฟล์ Subgrade Modulus",
        type=['docx'],
        key='subgrade_modulus',
        help="ไฟล์รายการคำนวณ Corrected Modulus of Subgrade Reaction"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ส่วนที่ 6: Cost Estimate (ถ้ามี)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**6. การประมาณราคาค่าก่อสร้าง** (ถ้ามี)")
    uploaded_files['cost_estimate'] = st.file_uploader(
        "เลือกไฟล์ประมาณราคา",
        type=['docx'],
        key='cost_estimate',
        help="ไฟล์รายงานการประมาณราคาค่าก่อสร้าง"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # แสดงสถานะไฟล์ที่อัปโหลด
    st.markdown("### 📊 สถานะไฟล์ที่อัปโหลด")
    
    file_count = sum(1 for f in uploaded_files.values() if f is not None)
    
    cols = st.columns(6)
    file_keys = list(uploaded_files.keys())
    file_labels = ['TF', 'ESALs', 'AC', 'JPCP', 'k-value', 'Cost']
    
    for i, (key, label) in enumerate(zip(file_keys, file_labels)):
        with cols[i]:
            if uploaded_files[key] is not None:
                st.success(f"✅ {label}")
            else:
                st.warning(f"⬜ {label}")
    
    st.markdown(f"**อัปโหลดแล้ว: {file_count} ไฟล์**")
    
    st.markdown("---")
    
    # ปุ่มรวมไฟล์
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        merge_button = st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True)
    
    if merge_button:
        # ตรวจสอบว่ามีไฟล์อย่างน้อย 1 ไฟล์
        if file_count == 0:
            st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            with st.spinner("กำลังรวมไฟล์และสร้างรายงาน..."):
                try:
                    # รวมเอกสาร
                    merged_doc = merge_documents(
                        uploaded_files,
                        section_titles,
                        project_name,
                        report_date_str
                    )
                    
                    # สร้างไฟล์ชั่วคราว
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # ตั้งชื่อไฟล์
                        base_filename = "รายงานออกแบบโครงสร้างชั้นทาง"
                        if project_name:
                            base_filename = f"รายงานออกแบบ_{project_name.replace(' ', '_')}"
                        
                        docx_path = os.path.join(temp_dir, f"{base_filename}.docx")
                        pdf_path = os.path.join(temp_dir, f"{base_filename}.pdf")
                        
                        # บันทึกไฟล์ Word
                        merged_doc.save(docx_path)
                        
                        # แปลงเป็น PDF
                        pdf_success = convert_to_pdf(docx_path, pdf_path)
                        
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.success("✅ รวมไฟล์เรียบร้อยแล้ว!")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # ปุ่มดาวน์โหลด
                        st.markdown("### 📥 ดาวน์โหลดรายงาน")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # ดาวน์โหลด Word
                            with open(docx_path, 'rb') as f:
                                docx_data = f.read()
                            st.download_button(
                                label="📄 ดาวน์โหลดไฟล์ Word (.docx)",
                                data=docx_data,
                                file_name=f"{base_filename}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )
                        
                        with col2:
                            # ดาวน์โหลด PDF
                            if pdf_success and os.path.exists(pdf_path):
                                with open(pdf_path, 'rb') as f:
                                    pdf_data = f.read()
                                st.download_button(
                                    label="📕 ดาวน์โหลดไฟล์ PDF",
                                    data=pdf_data,
                                    file_name=f"{base_filename}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            else:
                                st.warning("⚠️ ไม่สามารถแปลงเป็น PDF ได้ กรุณาดาวน์โหลดไฟล์ Word แล้วแปลงด้วยตนเอง")
                
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                    st.exception(e)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #718096; font-size: 14px;">
        <p>พัฒนาโดย ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม</p>
        <p>มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ</p>
        <p>© 2025 - Pavement Design Report Merger v1.0</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
