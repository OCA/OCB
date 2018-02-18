C:\Users\Administrator\PycharmProjects\OCB\venv64\Scripts\python.exe C:/Users/Administrator/PycharmProjects/OCB/odoo-bin -r odoo -w root --addons-path=C:/Users/Administrator/PycharmProjects/OCB/addons,C:/Users/Administrator/PycharmProjects/OCB/odoo/addons
自己设置dev环境

[用PYTHON-VIRTUALENV统一管理ODOO PYTHON依赖库](http://note.youdao.com/noteshare?id=a245883a04027945a4b059f134a9692e)

https://renjie.me/2015/12/07/%E7%94%A8python-virtualenv%E7%BB%9F%E4%B8%80%E7%AE%A1%E7%90%86odoo-python%E4%BE%9D%E8%B5%96%E5%BA%93/

https://devecho.com/v/2/

注意：1、不要有任何勾选 2、选择原始python.exe 3、windows下提前在venv环境下安装好pywin32


pip install -r requirements.txt -i https://pypi.doubanio.com/simple

注意
 
 [wiki](https://try.ucaitu.com/1CIO/OCB/wiki)
____

啓動參數如果有問題用odd-bin -help取得相關參數。

要下载 pywin32-221.win32-py2.7.exe 最新版本是221，安装win32而不是64

https://github.com/mhammond/pywin32/releases

安装自动备份插件需要安装pysftp
psycopg2==2.7.1
python-ldap==2.4.27

[windows下安装](http://www.jianshu.com/p/b4b46fc11c74)

pip install python_ldap-2.4.38-cp27-cp27m-win_amd64.whl

[pg安装](https://doc.odoo.com/6.0/zh_CN/install/windows/postgres/)

[详细安装指导例如安装pypiwin32](https://www.odoo.com/documentation/10.0/setup/install.html)

如果碰到页面无法正常显示问题，则http://127.0.0.1:8069/web?debug，激活开发者模式

npm c60e33887b073b28cccd861f2f07a27	application/javascript	application	1	2018-01-31 15:47:09.959381

[建立trigger解决odoo 11 安装应用后web页面为空的问题](http://odoo.net.cn/topic/4801/%E5%BB%BA%E7%AB%8Btrigger%E8%A7%A3%E5%86%B3odoo-11-%E5%AE%89%E8%A3%85%E5%BA%94%E7%94%A8%E5%90%8Eweb%E9%A1%B5%E9%9D%A2%E4%B8%BA%E7%A9%BA%E7%9A%84%E9%97%AE%E9%A2%98
)
http://blog.51cto.com/siweilai/2061133


For Odoo employees
------------------

To add the odoo-dev remote use this command:

    $ ./setup/setup_dev.py setup_git_dev

To fetch odoo merge pull requests refs use this command:

    $ ./setup/setup_dev.py setup_git_review

先执行 npm install underscore 在安装less
npm install -g less 解决显示"没有执行lessc"的问题

291638 住院號  出院記錄沒有蓋章和診斷證明