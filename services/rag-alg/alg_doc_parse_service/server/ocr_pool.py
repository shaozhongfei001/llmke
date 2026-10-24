from pathlib import Path
from typing import Literal

from .cache_pool import CachePool
from .thread_safe_object import ThreadSafeObject


class _OCRPool(CachePool):
    def load_ocrs(self, model_path: str, device: Literal['gpu', 'cpu'] = None):
        self.atomic.acquire()
        if not self.get(model_path):
            item = ThreadSafeObject(model_path, pool=self)
            self.set(model_path, item)
            with item.acquire(msg='初始化'):
                self.atomic.release()
                ocr_model_dict = {}

                from deepdoc.vision import OCR, LayoutRecognizer, TableStructureRecognizer
                ocr_model_dict['ocr'] = OCR(model_path)
                ocr_model_dict['laws_layouter'] = LayoutRecognizer('layout.laws', model_path)
                ocr_model_dict['manual_layouter'] = LayoutRecognizer('layout.manual', model_path)
                ocr_model_dict['paper_layouter'] = LayoutRecognizer('layout.paper', model_path)
                ocr_model_dict['layouter'] = LayoutRecognizer('layout', model_path)
                ocr_model_dict['tbl_det'] = TableStructureRecognizer(model_path)

                import xgboost as xgb
                updown_cnt_mdl = xgb.Booster()
                if device == 'gpu':
                    updown_cnt_mdl.set_param({'device': 'cuda'})
                updown_cnt_mdl.load_model(Path(model_path) / 'updown_concat_xgb.model')
                ocr_model_dict['updown_cnt_mdl'] = updown_cnt_mdl

                item.obj = ocr_model_dict
                item.finish_loading()
        else:
            self.atomic.release()
        return self.get(model_path).obj


ocr_pool = _OCRPool()
