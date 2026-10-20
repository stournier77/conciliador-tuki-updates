import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'APP_MAC'))
import sevens_files as files

class WindowsBrowserUploadTests(unittest.TestCase):
    def test_windows_restores_browser_uploader_and_does_not_open_external_dialog(self):
        def browser(*args,**kwargs):return 'browser-file'
        def native(*args,**kwargs):raise AssertionError('External picker must not run')
        native._sevens_original=browser
        with patch.object(files.platform,'system',return_value='Windows'),patch.object(files.st,'file_uploader',native),patch.object(files,'choose_file') as chooser,patch.object(files.st,'button') as button:
            files.install_native_uploaders(lambda:Path.cwd())
            self.assertIs(files.st.file_uploader,browser)
            self.assertEqual(files.st.file_uploader('TXT',key='txt_iata'),'browser-file')
            chooser.assert_not_called();button.assert_not_called()
            files.install_native_uploaders(lambda:Path.cwd())
            self.assertIs(files.st.file_uploader,browser)

    def test_windows_has_no_python_callback_to_leave_page_waiting(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as temp:
            app=Path(temp)/'preview.py'
            app.write_text('import streamlit as st\nfrom sevens_files import install_native_uploaders\nfrom pathlib import Path\ninstall_native_uploaders(lambda:Path.cwd())\nst.file_uploader("Archivo TXT",type=["txt"],key="txt_iata")\n')
            with patch.object(files.platform,'system',return_value='Windows'),patch.object(files,'choose_file') as picker:
                result=AppTest.from_file(str(app)).run()
                self.assertFalse(result.exception)
                self.assertFalse(any(b.key.startswith('desktop_pick_') for b in result.button))
                picker.assert_not_called()

if __name__=='__main__':unittest.main()
