from .check_proxies import ProxyCheckWindow
from .get_proxies import ProxyInputWindow
from .cleaner_thread import CleanerThread
from ..dcinside_cleaner import Cleaner
from .utils import resource_path
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import uic
import json
import sys
import os

main_form = uic.loadUiType(resource_path('./resources/ui/ui_main_window.ui'))[0]
about_dialog_form = uic.loadUiType(resource_path('./resources/ui/ui_about_dialog.ui'))[0]
logo_ico = resource_path('./resources/icon/logo_icon.ico')
logo_img = resource_path('./resources/img/logo_wide.png')

class MainWindow(QtWidgets.QMainWindow, main_form):
    p_type_dict = { 'p': 'posting', 'c': 'comment' }
    captcha_signal = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(logo_ico))

        self.id = ''
        self.pw = ''
        self.p_type = '' # 'posting' | 'comment'
        self.g_list = []
        self.proxy_list = []
        
        self.about_dialog : AboutDialog

        self.progress_cur = 0
        self.progress_max = 0

        self.cleaner_thread = CleanerThread(self.captcha_signal)
        self.cleaner = Cleaner()
        self.cleaner_thread.setCleaner(self.cleaner)

        self.cleaner_thread.event_signal.connect(self.deleteEvent)

        self.input_pw.returnPressed.connect(self.login)
        self.btn_login.clicked.connect(self.login)

        self.btn_get_posting.clicked.connect(lambda: self.getGallList('p'))
        self.btn_get_comment.clicked.connect(lambda: self.getGallList('c'))

        self.btn_start.clicked.connect(self.delete)

        self.action_add_proxy.triggered.connect(self.openProxyInputDialog)
        self.action_get_proxy.triggered.connect(self.getProxyList)
        self.action_about.triggered.connect(self.openAboutDialog)

        self.checkbox_proxy.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.group_box_gall.setEnabled(False)

    def openAboutDialog(self):
        self.about_dialog = AboutDialog()
        self.about_dialog.show()

    def getProxyList(self):
        try:
            name = QtWidgets.QFileDialog.getOpenFileName(self, '프록시 파일 열기', './', 'JSON files (*.json)')[0]
            with open(name, 'r') as file:
                data = json.loads(file.read())
                if data['title'] != 'dcinside_cleaner_proxy_list':
                    raise Exception
                self.proxy_list = data['data']
                self.checkbox_proxy.setText('프록시 사용 - ' + os.path.basename(name))
                self.checkbox_proxy.setEnabled(True)
        except:
            self.proxy_list = []
            QtWidgets.QMessageBox.warning(self, '파일 열기 실패', '올바른 파일이 아닙니다.')

    @QtCore.pyqtSlot(dict)
    def deleteEvent(self, event):
        if event['type'] == 'pages':
            self.log('글 목록 가져오는 중...')
            self.progress_cur = 0
            self.progress_max = event['data']
            self.progress_bar.setValue(0)

        elif event['type'] == 'posts':
            self.log(f'글 개수는 {event["data"]}개 입니다')
            self.log('글 삭제하는 중...')
            self.progress_cur = 0
            self.progress_max = event['data']
            self.progress_bar.setValue(0)

        elif event['type'] in ('page_update', 'post_update'):
            self.progress_cur += 1
            self.progress_bar.setValue(int((self.progress_cur / self.progress_max) * 100))

            if event['type'] == 'page_update':
                self.log(f"{event['data']['index'] + 1}번째 페이지 로딩...")

            else:
                self.log(f"{event['data']['del_no']}번 글 삭제")
                
            self.log(f"프록시는 {event['data']['proxy'] or 'X'}, 딜레이는 {event['data']['delay']}sec")

        elif event['type'] == 'ipblocked':
            self.log('IP 차단 감지')
            QtWidgets.QMessageBox.warning(self, '차단 안내', 'IP가 차단되었습니다.')

        elif event['type'] == 'captcha':
            self.log('캡차 감지')
            QtWidgets.QMessageBox.information(self, '캡차 안내', '캡차가 감지되었습니다.\n갤로그에 접속해 캡차를 해제한 후 확인을 눌러주세요.')
            self.captcha_signal.emit(True)

        elif event['type'] == 'complete':
            self.log('삭제 완료')
            QtWidgets.QMessageBox.information(self, '완료', '삭제 작업이 완료되었습니다.')
            self.progress_cur = 0
            self.progress_max = 0
            self.label_current_mode.setText('현재 모드: Unknown')
            self.progress_bar.setValue(0)
            self.group_box_gall.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.combo_box_gall.clear()
            self.cleaner_thread.quit()
            self.g_list = []
            self.p_type = ''
            self.updateUserInfo()

    def log(self, text):
        self.box_log.append(text)
        self.statusBar().showMessage(text, 1500)

    def setCursorWait(self):
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

    def restoreCursor(self):
        QtGui.QGuiApplication.restoreOverrideCursor()

    def login(self):
        self.id = self.input_id.text()
        self.pw = self.input_pw.text()
        self.log('로그인 중...')
        self.setCursorWait()
        res = self.cleaner.login(self.id, self.pw)
        self.updateUserInfo()
        self.restoreCursor()
        if res:
            self.log('로그인 성공')
            QtWidgets.QMessageBox.information(self, '로그인 안내', '로그인되었습니다')
            self.group_box_login.setEnabled(False)
        else:
            self.log('로그인 실패')
            QtWidgets.QMessageBox.warning(self, '로그인 안내', '로그인에 실패했습니다.')

        self.group_box_gall.setEnabled(True)

    def updateUserInfo(self):
        result = self.cleaner.getUserInfo()
        self.label_nickname.setText('닉네임: ' + result['nickname'])
        self.label_article_num.setText('글 개수: ' + result['article_num'])
        self.label_comment_num.setText('댓글 개수: ' + result['comment_num'])

    def getGallList(self, post_type):
        self.combo_box_gall.clear()

        self.g_list = []
        self.setCursorWait()
        self.p_type = self.p_type_dict[post_type]

        self.log('갤러리 목록 가져오는 중...')
        self.label_current_mode.setText('현재 모드: ' + (post_type == 'p' and '글' or '댓글'))

        gall_list = self.cleaner.getGallList(self.p_type)
        idx = 0

        for gno in gall_list:
            self.g_list.append(gno)
            self.combo_box_gall.addItem(f'{idx + 1}. {gall_list[gno]}')
            idx += 1

        self.restoreCursor()
        self.btn_start.setEnabled(True)

    def delete(self):
        if not self.g_list:
            return QtWidgets.QMessageBox.warning(self, '안내', '글 또는 댓글 목록을 불러온 후 삭제해 주세요.')
        elif self.checkbox_gall_all.isChecked():
            self.cleaner_thread.setDelInfo(self.g_list, self.p_type)
        else:
            idx = self.combo_box_gall.currentIndex()
            self.cleaner_thread.setDelInfo([self.g_list[idx]], self.p_type)
        
        if self.checkbox_proxy.isChecked():
            self.cleaner.setProxyList(self.proxy_list)

        self.group_box_gall.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.checkbox_proxy.setEnabled(False)
        self.cleaner_thread.start()

    def openProxyInputDialog(self):
        self.proxy_input_dialog = ProxyInputWindow()
        self.proxy_input_dialog.proxy_list_signal.connect(self.openProxyCheckDialog)
        self.proxy_input_dialog.show()
        
    @QtCore.pyqtSlot(list)
    def openProxyCheckDialog(self, proxy_list):
        self.proxy_check_dialog = ProxyCheckWindow(proxy_list)
        self.proxy_check_dialog.available_proxy_list_signal.connect(self.setAvailableProxyList)
        self.proxy_check_dialog.show()

    @QtCore.pyqtSlot(list)
    def setAvailableProxyList(self, available_list):
        self.proxy_list = available_list
        self.checkbox_proxy.setText('프록시 사용 - 확인된 리스트')
        self.checkbox_proxy.setEnabled(True)

class AboutDialog(QtWidgets.QDialog, about_dialog_form):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(logo_ico))

        pixmap = QtGui.QPixmap()
        pixmap.load(logo_img)
        pixmap = pixmap.scaledToWidth(600)

        self.logo_img.setPixmap(pixmap)

        self.label_info.setOpenExternalLinks(True)

def execute():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()