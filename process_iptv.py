#!/usr/bin/env python3
import re
import requests
import time
from datetime import datetime

# 用户代理，避免被屏蔽
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def download_m3u(url, retries=3):
    """下载M3U文件，支持重试"""
    for attempt in range(retries):
        try:
            print(f"正在下载: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # 检查内容是否有效
            content = response.text
            if '#EXTM3U' in content or '#EXTINF' in content:
                print(f"下载成功，内容大小: {len(content)} 字符")
                return content
            else:
                print(f"警告: 下载的内容可能不是有效的M3U文件")
                return content
                
        except Exception as e:
            print(f"下载失败 (尝试 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"所有重试失败，跳过此源")
                return None

def parse_m3u_channels(content):
    """解析M3U内容，提取频道信息"""
    channels = []
    
    if not content:
        return channels
        
    lines = content.split('\n')
    current_channel = {}
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 处理EXTINF行
        if line.startswith('#EXTINF:'):
            current_channel = {
                'extinf': line,
                'name': '',
                'group': '',
                'url': ''
            }
            
            # 提取频道名称
            name_match = re.search(r',(.*)', line)
            if name_match:
                current_channel['name'] = name_match.group(1).strip()
            
            # 提取分组信息
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                current_channel['group'] = group_match.group(1)
            else:
                # 尝试其他格式的分组
                group_match2 = re.search(r'group-title=([^,]+)', line)
                if group_match2:
                    current_channel['group'] = group_match2.group(1).replace('"', '')
                    
        # 处理URL行
        elif line and not line.startswith('#') and current_channel and 'url' not in current_channel:
            current_channel['url'] = line
            channels.append(current_channel.copy())
            current_channel = {}
    
    print(f"解析到 {len(channels)} 个频道")
    return channels

def process_source1(channels):
    """处理第一个源的频道"""
    categories = {
        '央视频道': [],
        '卫视频道': [],
        '央视咪咕': [],
        '卫视咪咕': []
    }
    
    for channel in channels:
        name = channel.get('name', '')
        
        # 转换为小写便于匹配
        name_lower = name.lower()
        
        # 检查是否包含cctv和MCP
        if 'cctv' in name_lower and 'mcp' in name_lower:
            categories['央视频道'].append(channel)
        
        # 检查是否包含卫视和MCP
        elif '卫视' in name and 'MCP' in name:
            categories['卫视频道'].append(channel)
        
        # 检查是否包含CCTV（央视咪咕）
        elif 'CCTV' in name and 'MCP' not in name:
            categories['央视咪咕'].append(channel)
        
        # 检查是否包含卫视（卫视咪咕）
        elif '卫视' in name and 'MCP' not in name:
            categories['卫视咪咕'].append(channel)
    
    print(f"源1处理结果:")
    for cat, chs in categories.items():
        print(f"  {cat}: {len(chs)} 个频道")
        
    return categories

def process_source2(channels):
    """处理第二个源的频道"""
    categories = {
        '游戏赛事': [],
        '虎牙影视': [],
        '咪视界bc': [],
        '冰茶体育': [],
        '凤凰频道': [],
        '影视频道': []
    }
    
    for channel in channels:
        group = channel.get('group', '')
        name = channel.get('name', '')
        
        # 根据分组进行分类
        if '游戏赛事' in group:
            categories['游戏赛事'].append(channel)
        elif '虎牙影视' in group:
            categories['虎牙影视'].append(channel)
        elif '咪视界bc' in group:
            categories['咪视界bc'].append(channel)
        elif '冰茶体育' in group:
            categories['冰茶体育'].append(channel)
        elif '粤语频道' in group:
            # 提取特定的凤凰频道
            if any(phoenix in name for phoenix in ['凤凰中文', '凤凰资讯', '凤凰香港']):
                categories['凤凰频道'].append(channel)
        elif '其他频道' in group:
            categories['影视频道'].append(channel)
    
    print(f"源2处理结果:")
    for cat, chs in categories.items():
        print(f"  {cat}: {len(chs)} 个频道")
        
    return categories

def create_m3u_output(categories_list):
    """创建最终的M3U输出"""
    # M3U头部
    output = '#EXTM3U x-tvg-url=""\n'
    output += f'# Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    output += f'# Source1: https://live.ottiptv.cc/iptv.m3u\n'
    output += f'# Source2: https://bc.188766.xyz/\n\n'
    
    total_channels = 0
    
    # 遍历所有分类
    for categories in categories_list:
        for category_name, channels in categories.items():
            if channels:
                output += f'# {category_name}\n'
                for channel in channels:
                    # 修改分组名称为当前分类
                    extinf = re.sub(
                        r'group-title="[^"]+"',
                        f'group-title="{category_name}"',
                        channel['extinf']
                    )
                    # 如果原始没有group-title，添加一个
                    if 'group-title' not in extinf:
                        extinf = extinf.replace('#EXTINF:', f'#EXTINF: group-title="{category_name}" ')
                    
                    output += f'{extinf}\n'
                    output += f'{channel["url"]}\n\n'
                    total_channels += 1
    
    output += f'# Total channels: {total_channels}\n'
    return output, total_channels

def main():
    print("开始处理IPTV频道...")
    print("=" * 50)
    
    all_categories = []
    
    # 处理第一个源
    print("\n[处理源1]")
    url1 = "https://live.ottiptv.cc/iptv.m3u?userid=8137863657&sign=2c8d82c9f17f480726d4770be9d0fb33fd0fcb31e1024448c36663605ea6a3f99e5bd467b68c287e3f0c07f85b95a188139aa3f19e227e251dc707bce0ededaab73ceeaddf6195&auth_token=54741b289e946919fc1c34ca88db58a4"
    content1 = download_m3u(url1)
    
    if content1:
        channels1 = parse_m3u_channels(content1)
        categories1 = process_source1(channels1)
        all_categories.append(categories1)
    else:
        print("源1处理失败，跳过")
    
    # 处理第二个源
    print("\n[处理源2]")
    url2 = "https://bc.188766.xyz/?url=https://live.188766.xyz&mishitong=true&mima=mianfeibuhuaqian&huikan=1"
    content2 = download_m3u(url2)
    
    if content2:
        channels2 = parse_m3u_channels(content2)
        categories2 = process_source2(channels2)
        all_categories.append(categories2)
    else:
        print("源2处理失败，跳过")
    
    # 生成最终的M3U文件
    if all_categories:
        print("\n[生成最终M3U文件]")
        m3u_content, total_channels = create_m3u_output(all_categories)
        
        # 保存到文件
        with open('iptv.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"✓ 已生成 iptv.m3u")
        print(f"✓ 总频道数: {total_channels}")
        
        # 统计各分类频道数
        print("\n[频道分类统计]")
        for categories in all_categories:
            for cat_name, channels in categories.items():
                if channels:
                    print(f"  {cat_name}: {len(channels)} 个频道")
    else:
        print("错误: 没有成功处理任何源")
        return False
    
    print("\n" + "=" * 50)
    print("处理完成!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
