#!/usr/bin/env python3
import re
import requests
import time
import os
import urllib.parse
from datetime import datetime

# 更完整的用户代理
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

# 文件映射关系
FILE_MAPPING = {
    'live1.m3u': '央视频道',
    'live2.m3u': '卫视频道',
    'live3.m3u': '央视咪咕',
    'live4.m3u': '卫视咪咕',
    'live5.m3u': '影视频道',
    'live6.m3u': '虎牙影视',
    'live7.m3u': '游戏赛事',
    'live8.m3u': '咪视界bc',
    'live9.m3u': '冰茶体育',
    'live10.m3u': '凤凰频道'
}

def download_m3u(url, retries=3):
    """下载M3U文件"""
    for attempt in range(retries):
        try:
            print(f"正在下载: {url[:100]}...")
            
            # 添加超时和重定向处理
            session = requests.Session()
            session.max_redirects = 5
            
            response = session.get(url, headers=HEADERS, timeout=60, verify=False, allow_redirects=True)
            
            print(f"状态码: {response.status_code}")
            print(f"响应大小: {len(response.content)} 字节")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # 检查编码
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            content = response.text
            
            # 调试：打印前500字符
            print("前500字符内容:")
            print(content[:500])
            
            if '#EXTM3U' in content or '#EXTINF' in content:
                print(f"✓ 成功获取M3U内容")
                return content
            else:
                # 尝试查找可能的频道行
                if 'http://' in content or 'https://' in content or ',CCTV' in content or ',卫视' in content:
                    print("⚠ 内容可能包含频道信息但缺少标准M3U头")
                    return content
                else:
                    print("✗ 内容看起来不是有效的M3U文件")
                    print(f"内容样本: {content[:200]}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            print(f"网络错误 (尝试 {attempt+1}/{retries}): {e}")
        except Exception as e:
            print(f"未知错误 (尝试 {attempt+1}/{retries}): {e}")
        
        if attempt < retries - 1:
            print(f"等待2秒后重试...")
            time.sleep(2)
    
    return None

def parse_m3u_channels(content):
    """解析M3U频道 - 更宽松的解析"""
    channels = []
    
    if not content:
        print("内容为空，无法解析")
        return channels
    
    print(f"开始解析内容，总长度: {len(content)} 字符")
    
    lines = content.split('\n')
    print(f"总行数: {len(lines)}")
    
    current_channel = {}
    extinf_found = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
        
        # 打印前几行用于调试
        if i < 10:
            print(f"第{i+1}行: {line[:100]}")
        
        # 检测EXTINF行（支持多种格式）
        if line.startswith('#EXTINF'):
            extinf_found = True
            current_channel = {
                'extinf': line,
                'name': '',
                'group': '',
                'url': ''
            }
            
            # 提取频道名称 - 更宽松的匹配
            # 格式可能是: #EXTINF:-1,频道名称
            # 或者: #EXTINF:-1 tvg-id="xxx" tvg-name="xxx" tvg-logo="xxx" group-title="xxx",频道名称
            
            # 查找最后一个逗号后的内容作为频道名
            last_comma = line.rfind(',')
            if last_comma > 0:
                channel_name = line[last_comma + 1:].strip()
                current_channel['name'] = channel_name
            
            # 提取分组信息
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                current_channel['group'] = group_match.group(1)
            else:
                # 尝试其他格式
                group_match = re.search(r'group-title=([^,\s]+)', line)
                if group_match:
                    current_channel['group'] = group_match.group(1).replace('"', '')
        
        # 检测URL行（以http或https开头）
        elif (line.startswith('http://') or line.startswith('https://') or 
              line.startswith('rtmp://') or line.startswith('rtsp://')):
            
            if current_channel and 'url' not in current_channel:
                current_channel['url'] = line
                channels.append(current_channel.copy())
                current_channel = {}
                extinf_found = False
            elif extinf_found and not current_channel:
                # 如果有EXTINF标记但没有捕获到完整信息，创建一个基本频道
                channels.append({
                    'extinf': '#EXTINF:-1,未知频道',
                    'name': '未知频道',
                    'group': '',
                    'url': line
                })
                extinf_found = False
    
    print(f"解析完成，找到 {len(channels)} 个频道")
    
    # 打印前5个频道的信息用于调试
    for i, channel in enumerate(channels[:5]):
        print(f"频道{i+1}: 名称='{channel.get('name', 'N/A')}', 分组='{channel.get('group', 'N/A')}'")
    
    return channels

def process_source1(channels):
    """处理第一个源 - 更宽松的匹配"""
    print("\n=== 处理第一个源 (ottiptv) ===")
    
    results = {
        'live1': [],  # cctv和MCP
        'live2': [],  # 卫视和MCP
        'live3': [],  # CCTV
        'live4': []   # 卫视
    }
    
    if not channels:
        print("没有频道可处理")
        return results
    
    for channel in channels:
        name = channel.get('name', '').upper()  # 转换为大写便于匹配
        
        print(f"检查频道: {name}")
        
        # 检查是否包含MCP
        has_mcp = 'MCP' in name
        
        # live1: 包含cctv和MCP
        if ('CCTV' in name or 'Cctv' in name or 'cctv' in name) and has_mcp:
            results['live1'].append(channel)
            print(f"  → 匹配 live1 (cctv和MCP)")
        
        # live2: 包含卫视和MCP
        elif ('卫视' in name or 'WEISHI' in name or 'weishi' in name) and has_mcp:
            results['live2'].append(channel)
            print(f"  → 匹配 live2 (卫视和MCP)")
        
        # live3: 包含CCTV (不包含MCP)
        elif ('CCTV' in name or 'Cctv' in name) and not has_mcp:
            results['live3'].append(channel)
            print(f"  → 匹配 live3 (CCTV)")
        
        # live4: 包含卫视 (不包含MCP)
        elif ('卫视' in name or 'WEISHI' in name or 'weishi' in name) and not has_mcp:
            results['live4'].append(channel)
            print(f"  → 匹配 live4 (卫视)")
    
    # 输出统计
    print(f"\n统计结果:")
    print(f"live1.m3u (央视频道): {len(results['live1'])} 个频道")
    print(f"live2.m3u (卫视频道): {len(results['live2'])} 个频道")
    print(f"live3.m3u (央视咪咕): {len(results['live3'])} 个频道")
    print(f"live4.m3u (卫视咪咕): {len(results['live4'])} 个频道")
    
    return results

def process_source2(channels):
    """处理第二个源"""
    print("\n=== 处理第二个源 (188766.xyz) ===")
    
    results = {
        'live5': [],   # 其他频道 -> 影视频道
        'live6': [],   # 虎牙影视
        'live7': [],   # 游戏赛事
        'live8': [],   # 咪视界bc
        'live9': [],   # 冰茶体育
        'live10': []   # 凤凰频道
    }
    
    if not channels:
        print("没有频道可处理")
        return results
    
    for channel in channels:
        group = channel.get('group', '')
        name = channel.get('name', '')
        
        print(f"检查频道: {name} (分组: {group})")
        
        # 转换为大写便于匹配
        group_upper = group.upper()
        name_upper = name.upper()
        
        # live7: 游戏赛事
        if '游戏' in group or '赛事' in group or 'GAME' in group_upper:
            results['live7'].append(channel)
            print(f"  → 匹配 live7 (游戏赛事)")
        
        # live6: 虎牙影视
        elif '虎牙' in group or 'HUYA' in group_upper:
            results['live6'].append(channel)
            print(f"  → 匹配 live6 (虎牙影视)")
        
        # live8: 咪视界bc
        elif '咪视' in group or 'MISHI' in group_upper:
            results['live8'].append(channel)
            print(f"  → 匹配 live8 (咪视界bc)")
        
        # live9: 冰茶体育
        elif '冰茶' in group or 'BINGCHA' in group_upper or '体育' in group:
            results['live9'].append(channel)
            print(f"  → 匹配 live9 (冰茶体育)")
        
        # live10: 凤凰频道
        elif ('粤语' in group or '凤凰' in name or 
              'FENGHUANG' in name_upper or 'PHOENIX' in name_upper):
            # 检查是否是特定的凤凰频道
            if any(phoenix in name for phoenix in ['凤凰中文', '凤凰资讯', '凤凰香港', 
                                                  'FENGHUANGZHONGWEN', 'FENGHUANGZIXUN', 
                                                  'FENGHUANGXIANGGANG']):
                results['live10'].append(channel)
                print(f"  → 匹配 live10 (凤凰频道)")
        
        # live5: 其他频道
        elif '其他' in group or 'OTHERS' in group_upper or '影视' in group:
            results['live5'].append(channel)
            print(f"  → 匹配 live5 (影视频道)")
    
    # 输出统计
    print(f"\n统计结果:")
    print(f"live5.m3u (影视频道): {len(results['live5'])} 个频道")
    print(f"live6.m3u (虎牙影视): {len(results['live6'])} 个频道")
    print(f"live7.m3u (游戏赛事): {len(results['live7'])} 个频道")
    print(f"live8.m3u (咪视界bc): {len(results['live8'])} 个频道")
    print(f"live9.m3u (冰茶体育): {len(results['live9'])} 个频道")
    print(f"live10.m3u (凤凰频道): {len(results['live10'])} 个频道")
    
    return results

def save_channel_file(channels, filename, category_name):
    """保存频道到文件"""
    print(f"\n保存文件: {filename} ({category_name})")
    
    content = f'#EXTM3U\n'
    content += f'# {category_name}\n'
    content += f'# 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    content += f'# 频道数量: {len(channels)}\n\n'
    
    if channels:
        for channel in channels:
            name = channel.get('name', '未知频道')
            extinf = channel.get('extinf', '')
            url = channel.get('url', '')
            
            # 如果extinf包含group-title，更新它
            if extinf and 'group-title=' in extinf:
                new_extinf = re.sub(r'group-title="[^"]+"', f'group-title="{category_name}"', extinf)
                content += f'{new_extinf}\n'
            else:
                # 创建新的EXTINF行
                tvg_id = re.search(r'tvg-id="([^"]+)"', extinf) if extinf else None
                tvg_logo = re.search(r'tvg-logo="([^"]+)"', extinf) if extinf else None
                
                tvg_id_str = f' tvg-id="{tvg_id.group(1)}"' if tvg_id else ''
                tvg_logo_str = f' tvg-logo="{tvg_logo.group(1)}"' if tvg_logo else ''
                
                content += f'#EXTINF:-1{tvg_id_str}{tvg_logo_str} group-title="{category_name}",{name}\n'
            
            content += f'{url}\n\n'
    else:
        content += f'# 暂无频道\n'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ 已保存 {len(channels)} 个频道到 {filename}")

def test_download():
    """测试下载功能"""
    print("\n=== 测试下载功能 ===")
    
    # 测试第一个URL
    url1 = "https://live.ottiptv.cc/iptv.m3u?userid=8137863657&sign=2c8d82c9f17f480726d4770be9d0fb33fd0fcb31e1024448c36663605ea6a3f99e5bd467b68c287e3f0c07f85b95a188139aa3f19e227e251dc707bce0ededaab73ceeaddf6195&auth_token=54741b289e946919fc1c34ca88db58a4"
    print(f"测试URL1: {url1[:80]}...")
    content1 = download_m3u(url1)
    
    if content1:
        print(f"URL1 内容长度: {len(content1)}")
        channels1 = parse_m3u_channels(content1)
        print(f"URL1 解析频道数: {len(channels1)}")
    else:
        print("URL1 下载失败")
    
    # 测试第二个URL
    url2 = "https://bc.188766.xyz/?url=https://live.188766.xyz&mishitong=true&mima=mianfeibuhuaqian&huikan=1"
    print(f"\n测试URL2: {url2}")
    content2 = download_m3u(url2)
    
    if content2:
        print(f"URL2 内容长度: {len(content2)}")
        channels2 = parse_m3u_channels(content2)
        print(f"URL2 解析频道数: {len(channels2)}")
    else:
        print("URL2 下载失败")
    
    return content1, content2

def create_combined_iptv():
    """创建整合的iptv.m3u文件"""
    print("\n=== 创建整合文件 ===")
    
    file_order = [
        'live1.m3u', 'live2.m3u', 'live3.m3u', 'live4.m3u',
        'live5.m3u', 'live6.m3u', 'live7.m3u', 'live8.m3u',
        'live9.m3u', 'live10.m3u'
    ]
    
    combined_content = '#EXTM3U\n'
    combined_content += f'# 整合IPTV频道列表\n'
    combined_content += f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    combined_content += f'# 来源: ottiptv.cc + bc.188766.xyz\n\n'
    
    total_channels = 0
    valid_files = 0
    
    for filename in file_order:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # 提取频道内容（跳过M3U头和注释）
                lines = file_content.split('\n')
                channel_lines = []
                in_channels = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('#EXTINF:'):
                        in_channels = True
                        channel_lines.append(line)
                    elif line.startswith('http://') or line.startswith('https://') or line.startswith('rtmp://') or line.startswith('rtsp://'):
                        if in_channels:
                            channel_lines.append(line)
                    elif line.startswith('#EXTM3U') or line.startswith('#'):
                        continue
                    else:
                        in_channels = False
                
                if channel_lines:
                    # 添加分类标题
                    category_name = FILE_MAPPING.get(filename, filename.replace('.m3u', ''))
                    combined_content += f'# {category_name}\n'
                    
                    # 添加频道内容
                    for line in channel_lines:
                        combined_content += f'{line}\n'
                    
                    combined_content += '\n'
                    
                    # 统计
                    channel_count = file_content.count('#EXTINF:')
                    total_channels += channel_count
                    valid_files += 1
                    print(f"  {filename}: {channel_count} 个频道 → 整合完成")
            except Exception as e:
                print(f"  {filename}: 读取错误 - {e}")
        else:
            print(f"  {filename}: 文件不存在，跳过")
    
    # 添加统计信息
    combined_content += f'# 总计: {total_channels} 个频道\n'
    combined_content += f'# 分类: {valid_files} 个\n'
    combined_content += f'# 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    
    # 保存整合文件
    with open('iptv.m3u', 'w', encoding='utf-8') as f:
        f.write(combined_content)
    
    print(f"\n✓ iptv.m3u 创建成功")
    print(f"✓ 总频道数: {total_channels}")
    print(f"✓ 有效分类: {valid_files} 个")
    
    return total_channels

def main():
    print("=" * 60)
    print("IPTV频道处理开始")
    print("=" * 60)
    
    # 首先测试下载
    content1, content2 = test_download()
    
    if not content1 and not content2:
        print("两个源都下载失败，无法继续处理")
        # 创建空文件
        for filename, category in FILE_MAPPING.items():
            save_channel_file([], filename, category)
        create_combined_iptv()
        return False
    
    # 处理第一个源
    channels1 = []
    if content1:
        channels1 = parse_m3u_channels(content1)
        print(f"\n源1解析到 {len(channels1)} 个频道")
        if channels1:
            source1_results = process_source1(channels1)
            
            # 保存源1的文件
            print("\n保存源1文件:")
            save_channel_file(source1_results['live1'], 'live1.m3u', '央视频道')
            save_channel_file(source1_results['live2'], 'live2.m3u', '卫视频道')
            save_channel_file(source1_results['live3'], 'live3.m3u', '央视咪咕')
            save_channel_file(source1_results['live4'], 'live4.m3u', '卫视咪咕')
        else:
            print("源1解析频道失败，创建空文件")
            for filename, category in [('live1.m3u', '央视频道'), ('live2.m3u', '卫视频道'), 
                                      ('live3.m3u', '央视咪咕'), ('live4.m3u', '卫视咪咕')]:
                save_channel_file([], filename, category)
    else:
        print("源1下载失败，创建空文件")
        for filename, category in [('live1.m3u', '央视频道'), ('live2.m3u', '卫视频道'), 
                                  ('live3.m3u', '央视咪咕'), ('live4.m3u', '卫视咪咕')]:
            save_channel_file([], filename, category)
    
    # 处理第二个源
    channels2 = []
    if content2:
        channels2 = parse_m3u_channels(content2)
        print(f"\n源2解析到 {len(channels2)} 个频道")
        if channels2:
            source2_results = process_source2(channels2)
            
            # 保存源2的文件
            print("\n保存源2文件:")
            save_channel_file(source2_results['live5'], 'live5.m3u', '影视频道')
            save_channel_file(source2_results['live6'], 'live6.m3u', '虎牙影视')
            save_channel_file(source2_results['live7'], 'live7.m3u', '游戏赛事')
            save_channel_file(source2_results['live8'], 'live8.m3u', '咪视界bc')
            save_channel_file(source2_results['live9'], 'live9.m3u', '冰茶体育')
            save_channel_file(source2_results['live10'], 'live10.m3u', '凤凰频道')
        else:
            print("源2解析频道失败，创建空文件")
            for filename, category in [('live5.m3u', '影视频道'), ('live6.m3u', '虎牙影视'),
                                      ('live7.m3u', '游戏赛事'), ('live8.m3u', '咪视界bc'),
                                      ('live9.m3u', '冰茶体育'), ('live10.m3u', '凤凰频道')]:
                save_channel_file([], filename, category)
    else:
        print("源2下载失败，创建空文件")
        for filename, category in [('live5.m3u', '影视频道'), ('live6.m3u', '虎牙影视'),
                                  ('live7.m3u', '游戏赛事'), ('live8.m3u', '咪视界bc'),
                                  ('live9.m3u', '冰茶体育'), ('live10.m3u', '凤凰频道')]:
            save_channel_file([], filename, category)
    
    # 创建整合文件
    total_channels = create_combined_iptv()
    
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"总生成文件: 11个 (10个分类 + 1个整合)")
    print(f"总频道数: {total_channels}")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    # 忽略SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    success = main()
    exit(0 if success else 1)
