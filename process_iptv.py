#!/usr/bin/env python3
import re
import requests
import time
import os
from datetime import datetime

# 用户代理
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
            print(f"正在下载: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            content = response.text
            if '#EXTM3U' in content or '#EXTINF' in content:
                print(f"下载成功: {len(content)} 字符")
                return content
            else:
                print(f"警告: 可能不是有效的M3U文件")
                return content
                
        except Exception as e:
            print(f"下载失败 (尝试 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None

def parse_m3u_channels(content):
    """解析M3U频道"""
    channels = []
    
    if not content:
        return channels
        
    lines = content.split('\n')
    current_channel = {}
    
    for line in lines:
        line = line.strip()
        
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
            
            # 提取分组
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                current_channel['group'] = group_match.group(1)
                
        elif line and not line.startswith('#') and current_channel and 'url' not in current_channel:
            current_channel['url'] = line
            channels.append(current_channel.copy())
            current_channel = {}
    
    return channels

def process_source1(channels):
    """处理第一个源"""
    print("\n=== 处理第一个源 ===")
    
    # 初始化结果
    results = {
        'live1': [],  # cctv和MCP
        'live2': [],  # 卫视和MCP
        'live3': [],  # CCTV
        'live4': []   # 卫视
    }
    
    for channel in channels:
        name = channel.get('name', '')
        
        # live1: 包含cctv和MCP
        if 'cctv' in name.lower() and 'MCP' in name:
            results['live1'].append(channel)
        
        # live2: 包含卫视和MCP
        elif '卫视' in name and 'MCP' in name:
            results['live2'].append(channel)
        
        # live3: 包含CCTV (不包含MCP)
        elif 'CCTV' in name and 'MCP' not in name:
            results['live3'].append(channel)
        
        # live4: 包含卫视 (不包含MCP)
        elif '卫视' in name and 'MCP' not in name:
            results['live4'].append(channel)
    
    # 输出统计
    print(f"live1.m3u (央视频道): {len(results['live1'])} 个频道")
    print(f"live2.m3u (卫视频道): {len(results['live2'])} 个频道")
    print(f"live3.m3u (央视咪咕): {len(results['live3'])} 个频道")
    print(f"live4.m3u (卫视咪咕): {len(results['live4'])} 个频道")
    
    return results

def process_source2(channels):
    """处理第二个源"""
    print("\n=== 处理第二个源 ===")
    
    # 初始化结果
    results = {
        'live5': [],   # 其他频道 -> 影视频道
        'live6': [],   # 虎牙影视
        'live7': [],   # 游戏赛事
        'live8': [],   # 咪视界bc
        'live9': [],   # 冰茶体育
        'live10': []   # 凤凰频道
    }
    
    for channel in channels:
        group = channel.get('group', '')
        name = channel.get('name', '')
        
        # live7: 游戏赛事
        if '游戏赛事' in group:
            results['live7'].append(channel)
        
        # live6: 虎牙影视
        elif '虎牙影视' in group:
            results['live6'].append(channel)
        
        # live8: 咪视界bc
        elif '咪视界bc' in group:
            results['live8'].append(channel)
        
        # live9: 冰茶体育
        elif '冰茶体育' in group:
            results['live9'].append(channel)
        
        # live10: 凤凰频道
        elif '粤语频道' in group:
            if any(phoenix in name for phoenix in ['凤凰中文', '凤凰资讯', '凤凰香港']):
                results['live10'].append(channel)
        
        # live5: 其他频道
        elif '其他频道' in group:
            results['live5'].append(channel)
    
    # 输出统计
    print(f"live5.m3u (影视频道): {len(results['live5'])} 个频道")
    print(f"live6.m3u (虎牙影视): {len(results['live6'])} 个频道")
    print(f"live7.m3u (游戏赛事): {len(results['live7'])} 个频道")
    print(f"live8.m3u (咪视界bc): {len(results['live8'])} 个频道")
    print(f"live9.m3u (冰茶体育): {len(results['live9'])} 个频道")
    print(f"live10.m3u (凤凰频道): {len(results['live10'])} 个频道")
    
    return results

def save_channel_file(channels, filename, category_name):
    """保存频道到文件"""
    if not channels:
        print(f"  {filename}: 无频道，创建空文件")
        # 创建空文件但包含基本信息
        content = f'#EXTM3U\n# {category_name}\n# 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n# 频道数量: 0\n'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return
    
    content = f'#EXTM3U x-tvg-url=""\n'
    content += f'# {category_name}\n'
    content += f'# 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    content += f'# 频道数量: {len(channels)}\n\n'
    
    for channel in channels:
        extinf = channel['extinf']
        # 更新分组名称为分类名称
        if 'group-title="' in extinf:
            extinf = re.sub(r'group-title="[^"]+"', f'group-title="{category_name}"', extinf)
        else:
            extinf = f'#EXTINF:-1 group-title="{category_name}",{channel["name"]}'
        
        content += f'{extinf}\n'
        content += f'{channel["url"]}\n\n'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ {filename}: 保存 {len(channels)} 个频道 ({category_name})")

def create_combined_iptv():
    """创建整合的iptv.m3u文件"""
    print("\n=== 创建整合文件 ===")
    
    # 按指定顺序的文件列表
    file_order = [
        'live1.m3u',   # 央视频道
        'live2.m3u',   # 卫视频道
        'live3.m3u',   # 央视咪咕
        'live4.m3u',   # 卫视咪咕
        'live5.m3u',   # 影视频道
        'live6.m3u',   # 虎牙影视
        'live7.m3u',   # 游戏赛事
        'live8.m3u',   # 咪视界bc
        'live9.m3u',   # 冰茶体育
        'live10.m3u'   # 凤凰频道
    ]
    
    combined_content = '#EXTM3U x-tvg-url=""\n'
    combined_content += f'# 整合IPTV频道列表\n'
    combined_content += f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
    combined_content += f'# 来源: ottiptv.cc + bc.188766.xyz\n\n'
    
    total_channels = 0
    valid_files = 0
    
    for filename in file_order:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # 提取频道内容（跳过注释和空行）
            lines = file_content.split('\n')
            channel_section = []
            in_channel_section = False
            
            for line in lines:
                if line.startswith('#EXTINF:'):
                    in_channel_section = True
                if in_channel_section and line.strip():
                    channel_section.append(line)
            
            if channel_section:
                # 添加分类标题
                category_name = FILE_MAPPING.get(filename, filename.replace('.m3u', ''))
                combined_content += f'# {category_name}\n'
                
                # 添加频道内容
                for line in channel_section:
                    combined_content += f'{line}\n'
                
                combined_content += '\n'
                
                # 统计
                channel_count = file_content.count('#EXTINF:')
                total_channels += channel_count
                valid_files += 1
                print(f"  {filename}: {channel_count} 个频道 → 整合完成")
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
    
    # 处理第一个源
    url1 = "https://live.ottiptv.cc/iptv.m3u?userid=8137863657&sign=2c8d82c9f17f480726d4770be9d0fb33fd0fcb31e1024448c36663605ea6a3f99e5bd467b68c287e3f0c07f85b95a188139aa3f19e227e251dc707bce0ededaab73ceeaddf6195&auth_token=54741b289e946919fc1c34ca88db58a4"
    content1 = download_m3u(url1)
    
    if content1:
        channels1 = parse_m3u_channels(content1)
        print(f"源1解析到 {len(channels1)} 个频道")
        source1_results = process_source1(channels1)
        
        # 保存源1的文件
        print("\n保存源1文件:")
        save_channel_file(source1_results['live1'], 'live1.m3u', '央视频道')
        save_channel_file(source1_results['live2'], 'live2.m3u', '卫视频道')
        save_channel_file(source1_results['live3'], 'live3.m3u', '央视咪咕')
        save_channel_file(source1_results['live4'], 'live4.m3u', '卫视咪咕')
    else:
        print("源1下载失败，创建空文件")
        # 创建空文件
        for filename, category in [('live1.m3u', '央视频道'), ('live2.m3u', '卫视频道'), 
                                  ('live3.m3u', '央视咪咕'), ('live4.m3u', '卫视咪咕')]:
            save_channel_file([], filename, category)
    
    # 处理第二个源
    url2 = "https://bc.188766.xyz/?url=https://live.188766.xyz&mishitong=true&mima=mianfeibuhuaqian&huikan=1"
    content2 = download_m3u(url2)
    
    if content2:
        channels2 = parse_m3u_channels(content2)
        print(f"源2解析到 {len(channels2)} 个频道")
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
        print("源2下载失败，创建空文件")
        # 创建空文件
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
    success = main()
    exit(0 if success else 1)
