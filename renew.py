# -*- coding: utf-8 -*-
"""
ArcticCloud VPS 自动续期脚本
"""
import os
import re
import time
import urllib3
from curl_cffi import requests

# 禁用 SSL 证书验证警告（服务器证书已过期）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SOCKS5 代理配置
socks5_proxy_url = os.environ.get("SOCKS5_PROXY", "")
proxy_config = {
    "http": socks5_proxy_url,
    "https": socks5_proxy_url
} if socks5_proxy_url else {}

if socks5_proxy_url:
    print(f"🌐 已配置 SOCKS5 代理: {socks5_proxy_url[:20]}...")
else:
    print("🌐 未配置代理，使用直连")

# ArcticCloud 配置
username = os.environ.get("ARCTIC_USERNAME", "")
password = os.environ.get("ARCTIC_PASSWORD", "")

if not username or not password:
    print("❌ 账号密码不全！请设置 ARCTIC_USERNAME 和 ARCTIC_PASSWORD 环境变量！")
    print("   示例: export ARCTIC_USERNAME='your_username'")
    print("   示例: export ARCTIC_PASSWORD='your_password'")
    exit(1)

print(f"✅ 已加载账号配置: {username[:3]}***")

# ArcticCloud 登录地址
LOGIN_URL = "https://vps.polarbear.nyc.mn/index/login/?referer=%2Fcontrol%2Findex%2F"
PRODUCT_LIST_URL = "https://vps.polarbear.nyc.mn/control/index/"
BASE_URL = "https://vps.polarbear.nyc.mn"

# Telegram 配置
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id = os.environ.get("TG_CHAT_ID", "")
thread_id = os.environ.get("THREAD_ID", "")
telegram_api_url = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

if telegram_bot_token and chat_id:
    print("✅ 已配置 Telegram 通知")
else:
    print("⚠️ 未配置 Telegram 通知，将仅显示控制台输出")

def send_telegram_notification(token, chat_id, message):
    """发送 Telegram 通知"""
    if not token or not chat_id:
        print("⚠️ Telegram 配置不全，跳过发送通知")
        return False
    
    api_url = f'{telegram_api_url}/bot{token}/sendMessage'
    notification_data = {
        'chat_id': chat_id,
        'text': message
    }
    
    if thread_id:
        notification_data['message_thread_id'] = thread_id
    
    try:
        response = requests.post(
            api_url, 
            json=notification_data, 
            timeout=30, 
            proxies=proxy_config,
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Telegram 通知发送成功")
                return True
            else:
                print(f"❌ Telegram API 返回错误: {result.get('description', '未知错误')}")
        else:
            print(f"❌ Telegram 请求失败: HTTP {response.status_code}")
        
        return False
        
    except Exception as error:
        print(f"❌ Telegram 通知发送失败: {error}")
        return False

def login_to_arcticcloud(login_url, username, password):
    """登录到 ArcticCloud 管理面板"""
    print(f"🔑 开始登录 ArcticCloud: {username[:3]}***")
    
    session = requests.Session(impersonate="chrome110")
    
    try:
        session.get(login_url, proxies=proxy_config, timeout=30, verify=False)
        
    except Exception as error:
        print(f"❌ 登录页访问失败: {error}")
        return None

    login_data = {
        "swapname": username,
        "swappass": password
    }
    
    request_headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
        'Origin': "https://vps.polarbear.nyc.mn",
        'Referer': login_url,
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8",
        'Accept-Encoding': "gzip, deflate, br",
        'Connection': "keep-alive",
        'Upgrade-Insecure-Requests': "1"
    }
    
    try:
        response = session.post(
            login_url, 
            data=login_data, 
            headers=request_headers, 
            proxies=proxy_config, 
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            response_text = response.text
            if '欢迎回来' in response_text or '退出登录' in response_text:
                print("✅ ArcticCloud 登录成功")
                return session
            elif '错误' in response_text or '失败' in response_text:
                print("❌ 登录失败: 用户名或密码错误")
            else:
                print("❌ 登录失败: 未知错误")
        else:
            print(f"❌ 登录请求失败: HTTP {response.status_code}")
            
    except Exception as error:
        print(f"❌ 登录异常: {error}")
    
    return None

def get_product_list_from_page(session):
    """从产品列表页面获取产品ID和管理URL"""
    print(f"📋 获取产品列表: {PRODUCT_LIST_URL}")
    
    try:
        response = session.get(PRODUCT_LIST_URL, proxies=proxy_config, timeout=60, verify=False)
        
        if response.status_code != 200:
            print(f"❌ 获取产品列表失败: HTTP {response.status_code}")
            return []
        
        print("✅ 成功获取产品列表页面")
        
        html_content = response.text
        
        manage_button_pattern = r'<a[^>]*class=["\'][^"\'>]*(?:btn[^"\'>]*btn-primary|btn-primary[^"\'>]*btn)[^"\'>]*["\'][^>]*href=["\']([^"\'>]*control/detail/(\d+)[^"\'>]*)["\'][^>]*>'
        matches = re.finditer(manage_button_pattern, html_content, re.IGNORECASE)
        
        product_ids = []
        manage_urls = []
        product_names = []  # 用于存储产品名称
        
        for match in matches:
            full_href = match.group(1)
            product_id = match.group(2)
            product_ids.append(product_id)
            manage_urls.append(full_href)
            # 提取产品名称：查找包含此管理按钮的<tr>元素，然后获取第2个<td>元素的文本
            product_name = "未知产品"
            # 查找包含此管理按钮的<tr>元素
            tr_start_pos = html_content.rfind('<tr', 0, match.start())
            tr_end_pos = html_content.find('</tr>', match.end())
            if tr_start_pos != -1 and tr_end_pos != -1:
                tr_content = html_content[tr_start_pos:tr_end_pos+5]
                # 查找所有的<td>元素
                td_matches = re.findall(r'<td[^>]*>(.*?)</td>', tr_content, re.DOTALL)
                # 获取第2个<td>元素的文本（索引为1）
                if len(td_matches) >= 2:
                    # 移除HTML标签并清理空白字符
                    product_name = re.sub(r'<[^>]+>', '', td_matches[1]).strip()
                    # 如果清理后为空，则使用原始内容
                    if not product_name:
                        product_name = td_matches[1].strip()
            
            product_names.append(product_name)  # 保存产品名称
            print(f"✅ 找到管理按钮: 产品ID {product_id}, 产品名称 {product_name}, URL: {full_href}")
        
        if not product_ids:
            fallback_pattern = r'href=["\']([^"\'>]*control/detail/(\d+)[^"\'>]*)["\']'
            fallback_matches = re.finditer(fallback_pattern, html_content, re.IGNORECASE)
            
            for match in fallback_matches:
                full_href = match.group(1)
                product_id = match.group(2)
                product_ids.append(product_id)
                manage_urls.append(full_href)
                product_names.append("未知产品")  # 为备用方案也添加产品名称
                print(f"⚠️ 备用方案找到: 产品ID {product_id}, URL: {full_href}")
        
        if not product_ids:
            print("❌ 未在页面中找到任何产品管理链接")
            return []
        
        unique_product_ids = list(set(product_ids))
        
        product_url_map = {}
        product_name_map = {}  # 用于存储产品ID到产品名称的映射
        for i, product_id in enumerate(product_ids):
            if product_id not in product_url_map:
                full_url = manage_urls[i]
                if not full_url.startswith('http'):
                    full_url = BASE_URL + ('' if full_url.startswith('/') else '/') + full_url
                product_url_map[product_id] = full_url
                product_name_map[product_id] = product_names[i]  # 保存产品名称映射
        
        products = []
        
        for product_id in unique_product_ids:
            manage_url = product_url_map.get(product_id, f'{BASE_URL}/control/detail/{product_id}/')
            product_name = product_name_map.get(product_id, f'VPS_{product_id}')  # 获取产品名称
            product_info = {
                'id': product_id,
                'name': product_name,  # 使用提取到的产品名称
                'manage_url': manage_url,
                'expiry_date': None
            }
            products.append(product_info)
        
        print(f"\n🎉 最终获取到 {len(products)} 个产品:")
        for product in products:
            print(f"   • 产品ID: {product['id']}, 产品名称: {product['name']}, 管理URL: {product['manage_url']}")
        
        return products
        
    except Exception as error:
        print(f"❌ 解析产品列表失败: {error}")
        return []

def _extract_expiry_from_manage_page(html_content):
    """从产品管理界面提取到期时间"""
    try:
        # 只保留模式1: 从 li.list-group-item 中提取包含"到期时间"后的日期
        expiry_pattern = r'<li[^>]*class=["\'][^"\'>]*list-group-item[^"\'>]*["\'][^>]*>[\s\S]*?到期时间[\s\S]*?([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)[\s\S]*?</li>'
        
        matches = re.finditer(expiry_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            potential_date = match.group(1).strip()
            
            if _is_valid_date_format(potential_date):
                print(f"📅 从管理界面li元素提取到期时间: {potential_date}")
                return potential_date
        
        print(f"⚠️ 未能从管理界面li元素提取到期时间")
        return None
        
    except Exception as error:
        print(f"⚠️ 从管理界面提取到期时间失败: {error}")
        return None

def _is_valid_date_format(date_str):
    """验证日期格式是否合理"""
    if not date_str:
        return False
    
    date_patterns = [
        r'^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$',
        r'^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}\s+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$',
        r'^[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}$',
        r'^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$',
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, date_str):
            try:
                numbers = re.findall(r'[0-9]+', date_str)
                if len(numbers) >= 3:
                    year, month, day = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return True
            except:
                pass
    
    return False

def renew_product(session, product):
    """对单个产品进行续期操作"""
    import time
    
    try:
        product_id = product['id']
        manage_url = product.get('manage_url', f"{BASE_URL}/control/detail/{product_id}/")
        
        print(f"🔄 开始续期操作: 产品 ID {product_id}")
        
        try:
            response = session.get(manage_url, proxies=proxy_config, timeout=60, verify=False)
            if response.status_code == 200:
                html_content = response.text
                
                # 直接使用从产品列表页面获取的产品名称，不再从管理页面重新获取
                actual_product_name = product.get('name', f'VPS_{product_id}')
                old_expiry = _extract_expiry_from_manage_page(html_content)
                
                # 不再更新产品名称，只保留到期时间
                product['expiry_date'] = old_expiry
                
            else:
                actual_product_name = product.get('name', f'VPS_{product_id}')
                old_expiry = product.get('expiry_date')
                
        except Exception as e:
            actual_product_name = product.get('name', f'VPS_{product_id}')
            old_expiry = product.get('expiry_date')
        
        pay_url = f"{BASE_URL}/control/detail/{product_id}/pay/"
        
        renew_response = session.post(pay_url, timeout=120, proxies=proxy_config, verify=False)
        
        if renew_response.status_code == 200 and "免费产品已经帮您续期到当前时间的最大续期时间" in renew_response.text:
            print(f"✅ {actual_product_name} 续期操作成功")
            
            new_expiry = _get_updated_expiry_from_manage_page(session, product_id, old_expiry)
            
            return {'success': True, 'expiry_date': new_expiry}
            
        else:
            print(f"❌ {actual_product_name} 续期操作失败: 状态码 {renew_response.status_code}")
            return {'success': False, 'expiry_date': old_expiry}
            
    except Exception as e:
        actual_product_name = product.get('name', f'VPS_{product.get("id", "unknown")}')
        print(f"❌ {actual_product_name} 续期请求异常: {e}")
        return {'success': False, 'expiry_date': product.get('expiry_date')}


def _get_updated_expiry_from_manage_page(session, product_id, old_expiry):
    """从产品管理界面获取续期后的新到期时间"""
    time.sleep(3)
    
    max_retries = 5
    retry_delays = [2, 3, 5, 8, 10]
    
    for attempt in range(max_retries):
        try:
            manage_url = f"{BASE_URL}/control/detail/{product_id}/"
            
            response = session.get(
                manage_url, 
                proxies=proxy_config, 
                timeout=60,
                verify=False,
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
            if response.status_code == 200:
                new_expiry = _extract_expiry_from_manage_page(response.text)
                
                if new_expiry:
                    if new_expiry != old_expiry:
                        print(f"✅ 检测到到期时间变化: {old_expiry} → {new_expiry}")
                        return new_expiry
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delays[attempt])
                        else:
                            return new_expiry
            
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                
        except Exception as error:
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
    
    final_expiry = old_expiry or '未知'
    return final_expiry


session = login_to_arcticcloud(LOGIN_URL, username, password)

if session:
    products = get_product_list_from_page(session)
    
    if not products:
        print("❌ 未找到任何产品，退出脚本")
        if telegram_bot_token and chat_id:
            send_telegram_notification(telegram_bot_token, chat_id, "ArcticCloud VPS续期提醒：\n\n❌未找到任何产品！😭")
        exit()
    
    success_count = 0
    fail_count = 0
    success_products = []
    failed_products = []
    
    for product in products:
        result = renew_product(session, product)
        if result['success']:
            success_count += 1
            success_products.append({
                'name': product['name'],
                'expiry_date': result['expiry_date'] or '未知'
            })
        else:
            fail_count += 1
            failed_products.append({
                'name': product['name'],
                'expiry_date': result['expiry_date'] or '未知'
            })
    
    # 发送汇总通知
    if telegram_bot_token and chat_id:
        summary_message = f"ArcticCloud VPS续期汇总：\n\n📊 总计: {len(products)} 个产品\n✅ 成功: {success_count} 个\n❌ 失败: {fail_count} 个"
        
        if success_products:
            summary_message += "\n\n✅ 成功续期的产品："
            for i, product in enumerate(success_products, 1):
                summary_message += f"\n{i}. {product['name']} (📅 {product['expiry_date']})"
        
        if failed_products:
            summary_message += "\n\n❌ 续期失败的产品："
            for i, product in enumerate(failed_products, 1):
                summary_message += f"\n{i}. {product['name']} (📅 {product['expiry_date']})"
        
        send_telegram_notification(telegram_bot_token, chat_id, summary_message)
    
    print(f"\n📊 续期完成汇总：")
    print(f"   总计: {len(products)} 个产品")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {fail_count} 个")
    
    if success_products:
        print(f"\n✅ 成功续期的产品：")
        for product in success_products:
            print(f"   - {product['name']} (到期时间: {product['expiry_date']})")
    
    if failed_products:
        print(f"\n❌ 续期失败的产品：")
        for product in failed_products:
            print(f"   - {product['name']} (当前到期: {product['expiry_date']})")
