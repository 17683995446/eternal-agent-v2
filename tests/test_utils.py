"""
工具函数模块测试

验证目标：
1. 文件操作正常
2. 时间处理正确
3. ID生成唯一
4. 列表/字典工具有效
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import (
    ensure_dir,
    read_json,
    write_json,
    read_text,
    write_text,
    file_exists,
    delete_file,
    now_iso,
    now_timestamp,
    parse_iso,
    format_duration,
    generate_uuid,
    generate_short_id,
    unique_list,
    chunk_list,
    deep_merge,
    is_valid_weight,
    clamp,
)


class TestFileOperations:
    """文件操作测试类"""
    
    def test_ensure_dir(self, tmp_path):
        """测试目录创建"""
        test_dir = tmp_path / "test" / "nested" / "dir"
        result = ensure_dir(test_dir)
        
        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir
    
    def test_write_and_read_json(self, tmp_path):
        """测试JSON读写"""
        test_file = tmp_path / "test.json"
        data = {"key": "value", "number": 123}
        
        # 写入
        assert write_json(test_file, data) == True
        
        # 读取
        result = read_json(test_file)
        assert result == data
    
    def test_read_json_nonexistent(self, tmp_path):
        """测试读取不存在的JSON文件"""
        test_file = tmp_path / "nonexistent.json"
        result = read_json(test_file, default={"default": True})
        assert result == {"default": True}
    
    def test_write_and_read_text(self, tmp_path):
        """测试文本读写"""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        
        assert write_text(test_file, content) == True
        assert read_text(test_file) == content
    
    def test_file_exists(self, tmp_path):
        """测试文件存在检查"""
        test_file = tmp_path / "test.txt"
        assert file_exists(test_file) == False
        
        write_text(test_file, "content")
        assert file_exists(test_file) == True
    
    def test_delete_file(self, tmp_path):
        """测试文件删除"""
        test_file = tmp_path / "test.txt"
        write_text(test_file, "content")
        
        assert delete_file(test_file) == True
        assert file_exists(test_file) == False


class TestTimeUtils:
    """时间工具测试类"""
    
    def test_now_iso(self):
        """测试ISO时间格式"""
        iso = now_iso()
        assert isinstance(iso, str)
        assert "T" in iso  # ISO格式包含T
    
    def test_now_timestamp(self):
        """测试时间戳"""
        ts = now_timestamp()
        assert isinstance(ts, float)
        assert ts > 0
    
    def test_parse_iso(self):
        """测试ISO解析"""
        iso = now_iso()
        dt = parse_iso(iso)
        assert dt is not None
    
    def test_format_duration(self):
        """测试时长格式化"""
        assert "s" in format_duration(30)
        assert "m" in format_duration(120)
        assert "h" in format_duration(7200)
        assert "d" in format_duration(172800)


class TestIDGeneration:
    """ID生成测试类"""
    
    def test_generate_uuid(self):
        """测试UUID生成"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID标准长度
        assert "-" in uuid1
    
    def test_generate_short_id(self):
        """测试短ID生成"""
        id1 = generate_short_id(8)
        id2 = generate_short_id(8)
        
        assert id1 != id2
        assert len(id1) == 8


class TestListDictUtils:
    """列表/字典工具测试类"""
    
    def test_unique_list(self):
        """测试列表去重"""
        items = [1, 2, 2, 3, 3, 3, 4]
        result = unique_list(items)
        
        assert result == [1, 2, 3, 4]
    
    def test_chunk_list(self):
        """测试列表分块"""
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = chunk_list(items, 3)
        
        assert len(chunks) == 3
        assert chunks[0] == [1, 2, 3]
        assert chunks[1] == [4, 5, 6]
        assert chunks[2] == [7]
    
    def test_deep_merge(self):
        """测试深度合并"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        
        result = deep_merge(dict1, dict2)
        
        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 3
        assert result["e"] == 4


class TestValidation:
    """验证工具测试类"""
    
    def test_is_valid_weight(self):
        """测试权重验证"""
        assert is_valid_weight(0.0) == True
        assert is_valid_weight(0.5) == True
        assert is_valid_weight(1.0) == True
        assert is_valid_weight(-0.1) == False
        assert is_valid_weight(1.1) == False
    
    def test_clamp(self):
        """测试值限制"""
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
