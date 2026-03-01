import os
import tempfile
import zipfile

def download_scan_items(scan_item_dir, problem_type):
    # 创建临时ZIP文件
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    zip_path = temp_zip.name
    temp_zip.close()

    with zipfile.ZipFile(zip_path, 'w') as zf:
        # 添加该scan_item的所有CSV文件
        for file in os.listdir(scan_item_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(scan_item_dir, file)
                folder_name = problem_type + '/'
                folder_name_all = os.path.join(folder_name, file)
                zf.write(file_path, folder_name_all)

    return zip_path, problem_type