import os
import time
import random
import logging
import sys
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# --------------------------
# 配置与常量定义（可根据需求调整）
# --------------------------
# 等待时间配置（单位：秒）
MAX_WAIT_TIME = 30  # 元素等待最长时间
PAGE_LOAD_TIMEOUT = 60  # 页面加载超时时间
IMPLICIT_WAIT = 20  # 隐式等待时间
LOGIN_AFTER_WAIT = 10  # 登录后等待时间
FOLLOW_ACTION_DELAY = (5, 10)  # 关注操作间的随机延迟范围

# 目标配置
TARGET_PAGE_URL = "https://github.com/DennisThink/awesome_twitter_CN"  # 提取用户列表的页面
TWITTER_LOGIN_URL = "https://twitter.com/login"  # Twitter登录页
CHROME_BINARY_PATH = "/opt/google/chrome/chrome"  # Chrome浏览器路径（根据系统调整）

# 日志配置
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO


# --------------------------
# 工具函数
# --------------------------
def setup_logging():
    """初始化日志配置，确保中文正常输出"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        stream=sys.stdout
    )
    # 修正标准输出编码为UTF-8，避免中文乱码
    if sys.stdout.encoding != 'UTF-8':
        sys.stdout.reconfigure(encoding='UTF-8')
    return logging.getLogger(__name__)


def create_chrome_options():
    """创建Chrome浏览器配置（反检测+性能优化）"""
    options = Options()
    # 浏览器运行模式与性能配置
    options.add_argument("--headless")  # 无头模式（无界面运行）
    options.add_argument("--no-sandbox")  # 绕过沙箱限制
    options.add_argument("--disable-dev-shm-usage")  # 解决内存不足问题
    options.add_argument("--disable-gpu")  # 禁用GPU加速（无头模式下无需）
    options.add_argument("--start-maximized")  # 最大化窗口（避免元素位置异常）
    
    # 反自动化检测配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.58 Safari/537.36"
    )
    
    # 指定Chrome可执行文件路径（根据系统调整）
    options.binary_location = CHROME_BINARY_PATH
    return options


def init_webdriver():
    """初始化WebDriver实例"""
    logger.info("正在初始化Chrome浏览器驱动...")
    chrome_options = create_chrome_options()
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    # 设置超时配置
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver


def safe_click(driver, xpath):
    """安全点击元素（等待元素可点击后再执行）"""
    try:
        element = WebDriverWait(driver, MAX_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        # 使用JS点击避免元素被遮挡的问题
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        logger.error(f"点击元素失败（XPATH: {xpath}）：{str(e)}")
        return False


# --------------------------
# 核心功能函数
# --------------------------
def twitter_login(driver, username, password):
    """登录Twitter账户"""
    logger.info("开始执行Twitter登录流程")
    driver.get(TWITTER_LOGIN_URL)
    time.sleep(5)  # 等待登录页初始加载
    
    logger.info(f"当前页面：{driver.title}（{driver.current_url}）")
    
    # 检测安全验证（如验证码）
    if "challenge" in driver.current_url or "security" in driver.current_url:
        logger.warning("检测到安全验证！请手动完成验证后继续")
        input("完成验证后按回车键继续...")
    
    try:
        # 输入用户名并点击下一步
        username_input = WebDriverWait(driver, MAX_WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='text']"))
        )
        username_input.send_keys(username)
        safe_click(driver, "//span[text()='Next']")  # 点击"下一步"按钮
        
        # 输入密码并点击登录
        password_input = WebDriverWait(driver, MAX_WAIT_TIME).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_input.send_keys(password)
        safe_click(driver, "//span[text()='Log in']")  # 点击"登录"按钮
        
        # 验证登录成功（跳转至首页）
        WebDriverWait(driver, MAX_WAIT_TIME).until(EC.url_contains("home"))
        logger.info("Twitter登录成功！")
        return True
    except Exception as e:
        logger.error(f"登录失败：{str(e)}", exc_info=True)
        raise


def extract_twitter_usernames(driver):
    """从当前页面提取有效的Twitter用户名"""
    logger.info("开始提取页面中的Twitter用户链接")
    
    # 匹配Twitter用户链接的正则（支持twitter.com和x.com）
    twitter_url_pattern = re.compile(
        r'https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?$'
    )
    
    # 提取所有带链接的元素
    all_links = driver.find_elements(By.XPATH, "//a[@href]")
    usernames = []
    
    for link in all_links:
        href = link.get_attribute("href")
        if not href:
            continue
        
        # 匹配并提取用户名
        match_result = twitter_url_pattern.match(href)
        if match_result:
            username = match_result.group(1)
            if username not in usernames:  # 去重
                usernames.append(username)
    
    logger.info(f"共提取到 {len(usernames)} 个有效Twitter用户名")
    return usernames


def follow_user(driver, username):
    """关注指定Twitter用户"""
    logger.info(f"开始处理用户：@{username}")
    user_page_url = f"https://twitter.com/{username}"
    
    try:
        # 访问用户主页
        driver.get(user_page_url)
        WebDriverWait(driver, MAX_WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # 多次尝试寻找关注按钮（应对页面加载延迟）
        follow_button = None
        for attempt in range(5):
            try:
                # 匹配"关注"或"Follow"按钮（支持中英文）
                follow_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//span[contains(@class, 'css-1jxf684') and .//span[text()='关注' or text()='Follow']]"
                    ))
                )
                break
            except:
                logger.info(f"第 {attempt+1} 次尝试：未找到关注按钮，刷新页面重试")
                driver.refresh()
                time.sleep(3)
        
        if not follow_button:
            logger.warning(f"无法找到@{username}的关注按钮，跳过该用户")
            return False
        
        # 执行关注操作
        driver.execute_script("arguments[0].click();", follow_button)
        logger.info(f"成功关注用户：@{username}")
        return True
    
    except Exception as e:
        logger.warning(f"处理用户@{username}时出错：{str(e)}")
        return False


def batch_follow_from_page(driver, target_page_url):
    """从目标页面提取用户并批量关注"""
    logger.info(f"开始访问目标页面：{target_page_url}")
    try:
        # 访问目标页面并等待加载完成
        driver.get(target_page_url)
        WebDriverWait(driver, MAX_WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # 提取用户列表
        usernames = extract_twitter_usernames(driver)
        if not usernames:
            logger.warning("未提取到任何用户，终止批量关注流程")
            return
        
        # 逐个关注用户（添加随机延迟避免被限制）
        for username in usernames:
            follow_user(driver, username)
            delay = random.uniform(*FOLLOW_ACTION_DELAY)
            logger.info(f"等待 {delay:.1f} 秒后继续下一个用户...")
            time.sleep(delay)
    
    except Exception as e:
        logger.error(f"批量关注过程出错：{str(e)}", exc_info=True)


# --------------------------
# 主程序入口
# --------------------------
def main():
    # 初始化日志
    global logger
    logger = setup_logging()
    logger.info("===== Twitter批量关注工具启动 =====")
    
    # 获取账号信息（优先从环境变量读取，其次使用默认值）
    twitter_username = os.environ.get("TWITTER_USERNAME", "your_username")
    twitter_password = os.environ.get("TWITTER_PASSWORD", "your_password")
    
    # 初始化浏览器驱动
    driver = None
    try:
        driver = init_webdriver()
        
        # 执行登录流程
        twitter_login(driver, twitter_username, twitter_password)
        time.sleep(LOGIN_AFTER_WAIT)  # 登录后等待页面稳定
        
        # 执行批量关注
        logger.info("登录成功，准备开始批量关注流程")
        batch_follow_from_page(driver, TARGET_PAGE_URL)
    
    except Exception as e:
        logger.error(f"程序执行出错：{str(e)}", exc_info=True)
    
    finally:
        # 确保浏览器正确关闭
        if driver:
            logger.info("关闭浏览器实例")
            driver.quit()
        logger.info("===== 程序执行结束 =====")


if __name__ == "__main__":
    main()