import unittest
import asyncio
import os
import io
from pathlib import Path
from dotenv import load_dotenv
from fastapi import UploadFile

# Ensure environment is loaded from agent_backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from api.routes import verify_internal_api_key
from fastapi import HTTPException
from services.image_storage import save_uploaded_image
from services.storage_manager import storage_manager
from agents.disease.classifier import disease_qa_prompt
from agents.crop.graph import CROP_AGENT_PROMPT
from agents.general.graph import GENERAL_REASONING_PROMPT


class TestSecurityHardening(unittest.TestCase):
    """Phase 6 Test Suite: Internal Auth, Path Traversal, XML Fencing & Concurrency."""

    def test_01_internal_api_key_authentication(self):
        """Verify endpoints reject unauthenticated internal requests with HTTP 401."""
        valid_secret = os.getenv("INTERNAL_API_SECRET", "test_secret")
        os.environ["INTERNAL_API_SECRET"] = valid_secret

        # 1. Missing key
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verify_internal_api_key(x_internal_api_key=None))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail.get("error", {}).get("code"), "UNAUTHORIZED")

        # 2. Invalid key
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verify_internal_api_key(x_internal_api_key="wrong_secret_123"))
        self.assertEqual(ctx.exception.status_code, 401)

        # 3. Valid key
        # Should not raise exception
        asyncio.run(verify_internal_api_key(x_internal_api_key=valid_secret))

    def test_02_path_traversal_prevention(self):
        """Verify storage manager and upload handlers prevent directory traversal."""
        # 1. Traversal key in storage manager
        bad_keys = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "img_../../../evil.jpg",
            "/absolute/root/path"
        ]
        for key in bad_keys:
            resolved = storage_manager.get_image_path_from_key(key)
            self.assertIsNone(resolved, f"Security hole: key '{key}' was resolved to path: {resolved}!")

        # 2. Traversal deletion
        self.assertFalse(storage_manager.delete_by_key("../../evil.jpg"))

    def test_03_xml_boundary_fencing_in_prompts(self):
        """Verify untrusted RAG and web search data are wrapped in XML boundary tags."""
        # 1. Disease QA Prompt
        disease_prompt_str = str(disease_qa_prompt.messages)
        self.assertIn("<untrusted_evidence", disease_prompt_str, "Disease QA prompt missing <untrusted_evidence> fencing!")
        self.assertIn("</untrusted_evidence>", disease_prompt_str)
        self.assertIn("SECURITY INSTRUCTION", disease_prompt_str)

        # 2. Crop Agent Prompt
        self.assertIn("<untrusted_evidence", CROP_AGENT_PROMPT, "Crop prompt missing <untrusted_evidence> fencing!")
        self.assertIn("</untrusted_evidence>", CROP_AGENT_PROMPT)
        self.assertIn("SECURITY & GROUNDING RULES", CROP_AGENT_PROMPT)

        # 3. General Agent Prompt
        self.assertIn("<untrusted_evidence", GENERAL_REASONING_PROMPT, "General prompt missing <untrusted_evidence> fencing!")
        self.assertIn("</untrusted_evidence>", GENERAL_REASONING_PROMPT)
        self.assertIn("SECURITY RULE", GENERAL_REASONING_PROMPT)

    def test_04_async_non_blocking_image_processing(self):
        """Verify image processing executes asynchronously without blocking the loop."""
        from PIL import Image
        img_byte_arr = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="green")
        img.save(img_byte_arr, format="JPEG")
        raw_bytes = img_byte_arr.getvalue()

        upload_file = UploadFile(
            filename="safe_leaf.jpg",
            file=io.BytesIO(raw_bytes)
        )

        async def run_concurrent():
            # Run image save concurrently with another coroutine
            task1 = save_uploaded_image(upload_file)
            async def helper():
                await asyncio.sleep(0.01)
                return "completed"
            task2 = helper()
            res1, res2 = await asyncio.gather(task1, task2)
            return res1, res2

        res1, res2 = asyncio.run(run_concurrent())
        self.assertEqual(res2, "completed")
        self.assertTrue(res1["path"].endswith(".jpg"))
        self.assertTrue(res1["image_key"].startswith("img_"))

        # Clean up
        Path(res1["path"]).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

