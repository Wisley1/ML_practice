import os
import time
from typing import Any

import httpx
import streamlit as st

try:
    API_BASE = str(st.secrets["API_BASE"])
except (FileNotFoundError, KeyError, TypeError):
    API_BASE = os.environ.get("ML_API_BASE", "http://localhost:8000")

for key, default in (
    ("token", None),
    ("user_email", None),
    ("models_cache", None),
):
    if key not in st.session_state:
        st.session_state[key] = default


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("token")
    if not token:
        raise RuntimeError("Сначала войдите в аккаунт.")
    return {"Authorization": f"Bearer {token}"}


def register(email: str, password: str) -> bool:
    with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
        r = client.post("/auth/register", json={"email": email, "password": password})
        if r.status_code == 409:
            st.error("Этот email уже занят.")
            return False
        r.raise_for_status()
    st.session_state["user_email"] = email
    return True


def login(email: str, password: str) -> None:
    with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
        r = client.post("/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        st.session_state["token"] = r.json()["access_token"]
    st.session_state["user_email"] = email


def logout() -> None:
    st.session_state["token"] = None
    st.session_state["user_email"] = None
    st.session_state["models_cache"] = None
    st.session_state.pop("_flash_prediction_ok", None)
    st.session_state.pop("_pending_main_tab", None)
    st.session_state.pop("_admin_users", None)


def load_models() -> list[dict[str, Any]]:
    with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
        r = client.get("/models")
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise TypeError(f"Ожидался список моделей, пришло: {type(data)}")
        return data


def fetch_wallet() -> dict[str, Any]:
    with httpx.Client(base_url=API_BASE, headers=_auth_headers(), timeout=60.0) as client:
        r = client.get("/wallet/me")
        r.raise_for_status()
        return r.json()


def fetch_user_me() -> dict[str, Any]:
    with httpx.Client(base_url=API_BASE, headers=_auth_headers(), timeout=60.0) as client:
        r = client.get("/users/me")
        r.raise_for_status()
        return r.json()


def fetch_admin_users() -> list[dict[str, Any]]:
    with httpx.Client(base_url=API_BASE, headers=_auth_headers(), timeout=60.0) as client:
        r = client.get("/admin/users")
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise TypeError("admin/users: ожидался список")
        return data


def mock_topup(credits_to_add: int) -> dict[str, Any]:
    with httpx.Client(base_url=API_BASE, headers=_auth_headers(), timeout=60.0) as client:
        r = client.post("/billing/mock-topup", json={"credits_to_add": credits_to_add})
        r.raise_for_status()
        return r.json()


def submit_prediction(
    model_id: int,
    text: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    headers = _auth_headers()
    if idempotency_key and idempotency_key.strip():
        headers = {**headers, "Idempotency-Key": idempotency_key.strip()}
    with httpx.Client(base_url=API_BASE, headers=headers, timeout=60.0) as client:
        r = client.post("/predictions", json={"model_id": model_id, "text": text})
        r.raise_for_status()
        return r.json()


def poll_prediction(
    job_id: int,
    placeholder: Any = None,
    max_wait_sec: float = 120.0,
    interval_sec: float = 0.7,
) -> dict[str, Any] | None:
    deadline = time.monotonic() + max_wait_sec
    with httpx.Client(base_url=API_BASE, headers=_auth_headers(), timeout=60.0) as client:
        while time.monotonic() < deadline:
            r = client.get(f"/predictions/{job_id}")
            r.raise_for_status()
            data = r.json()
            status = data.get("status", "")
            if placeholder is not None:
                placeholder.info(f"Статус job **#{job_id}**: `{status}`")
            if status in ("completed", "failed"):
                return data
            time.sleep(interval_sec)
    return None


TAB_PREDICT, TAB_WALLET, TAB_MODELS, TAB_HELP, TAB_ADMIN = (
    "Предсказание",
    "Кошелёк",
    "Модели",
    "Справка",
    "Админ",
)


def _show_prediction_flash(flash: dict[str, Any]) -> None:
    res = flash.get("result") or {}
    if "label" in res:
        st.metric("Метка", str(res["label"]))
    if res.get("score") is not None:
        st.metric("Уверенность (лучший класс)", f"{float(res['score']):.4f}")
    cp = res.get("class_probabilities")
    if isinstance(cp, dict) and cp:
        ordered = sorted(cp.items(), key=lambda kv: -kv[1])
        parts = [f"{k}={float(v):.4f}" for k, v in ordered]
        st.caption("Вероятности по классам: " + " · ".join(parts))
    with st.expander("Полный JSON"):
        st.json(flash)


def main() -> None:
    st.set_page_config(page_title="ML Service", page_icon="🤖", layout="wide")
    st.title("Сервис классификации отзывов")
    st.caption(f"API: `{API_BASE}`")

    with st.sidebar:
        st.subheader("Аккаунт")
        if st.session_state["token"]:
            st.success("Вы вошли")
            st.text(st.session_state.get("user_email") or "")
            try:
                me = fetch_user_me()
                st.session_state["user_role"] = me.get("role", "user")
                loyalty = me.get("loyalty") or {}
                tier = loyalty.get("tier_name") or "bronze"
                disc = loyalty.get("discount_percentage")
                st.caption("Лояльность")
                st.markdown(f"**Уровень:** `{tier}`")
                if disc is not None:
                    st.markdown(f"**Скидка на предсказания:** {disc} %")
                st.caption(
                    "Уровень повышается после успешных предиктов (пороги — во вкладке «Справка»). "
                    "Раз в месяц счётчик периода обнуляется, уровень пересчитывается по итогам периода."
                )
            except Exception as e:
                st.warning(f"Не удалось загрузить профиль: {e}")
            if st.button("Выйти", use_container_width=True):
                logout()
                st.rerun()
        else:
            email_in = st.text_input("Email", key="login_email")
            password_in = st.text_input("Пароль", type="password", key="login_password")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Войти", use_container_width=True):
                    if not email_in or not password_in:
                        st.error("Укажите email и пароль (мин. 8 символов).")
                    else:
                        try:
                            login(email_in, password_in)
                            st.rerun()
                        except httpx.HTTPStatusError as e:
                            st.error(f"Ошибка входа: {e.response.status_code} — {e.response.text}")
            with c2:
                if st.button("Регистрация", use_container_width=True):
                    if not email_in or not password_in:
                        st.error("Укажите email и пароль.")
                    else:
                        try:
                            if register(email_in, password_in):
                                login(email_in, password_in)
                                st.rerun()
                        except httpx.HTTPStatusError as e:
                            st.error(f"Ошибка: {e.response.text}")

    if not st.session_state["token"]:
        st.info("Войдите или зарегистрируйтесь в боковой панели.")
        return

    flash = st.session_state.pop("_flash_prediction_ok", None)
    if flash:
        st.success("Готово")
        _show_prediction_flash(flash)

    pending_tab = st.session_state.pop("_pending_main_tab", None)
    if pending_tab is not None:
        st.session_state["app_main_tab"] = pending_tab

    choice = st.radio(
        "Раздел",
        [TAB_PREDICT, TAB_WALLET, TAB_MODELS, TAB_HELP, TAB_ADMIN],
        horizontal=True,
        key="app_main_tab",
        label_visibility="collapsed",
    )

    if choice == TAB_WALLET:
        st.subheader("Баланс и пополнение")
        if st.button("Обновить баланс", key="refresh_wallet"):
            try:
                w = fetch_wallet()
                st.session_state["_last_wallet"] = w
            except Exception as e:
                st.error(str(e))
        if "_last_wallet" not in st.session_state:
            try:
                st.session_state["_last_wallet"] = fetch_wallet()
            except Exception as e:
                st.error(str(e))
                st.session_state["_last_wallet"] = None
        w = st.session_state.get("_last_wallet")
        if isinstance(w, dict):
            st.metric("Кредиты", w.get("balance_credits", 0))
        credits = st.number_input("Сумма пополнения (кредиты)", min_value=1, value=10, step=1)
        if st.button("Пополнить (mock)"):
            try:
                resp = mock_topup(int(credits))
                st.success(f"Платёж #{resp.get('payment_id')} — баланс: {resp.get('balance_credits')}")
                st.session_state["_last_wallet"] = fetch_wallet()
                st.rerun()
            except httpx.HTTPStatusError as e:
                st.error(f"{e.response.status_code}: {e.response.text}")

    elif choice == TAB_PREDICT:
        st.subheader("Запуск классификации")
        if st.button("Загрузить список моделей", key="btn_load_models_predict"):
            try:
                st.session_state["models_cache"] = load_models()
                n = len(st.session_state["models_cache"])
                if n == 0:
                    st.warning(
                        "API вернул **0 моделей**. Засей БД: "
                        "`docker compose exec api python -m scripts.seed_ml_models`"
                    )
                else:
                    st.success(f"Загружено моделей: **{n}**")
                st.rerun()
            except httpx.HTTPStatusError as e:
                st.error(f"HTTP {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                st.error(
                    f"Нет связи с API `{API_BASE}`: {e}\n\n"
                    "Проверь, что контейнер `api` запущен и порт 8000 доступен."
                )
            except Exception as e:
                st.error(str(e))
        models = st.session_state.get("models_cache")
        if models is None:
            st.info("Нажми **«Загрузить список моделей»**, чтобы подтянуть каталог с API.")
        elif len(models) == 0:
            st.warning(
                "Список моделей пуст. Выполни: "
                "`docker compose exec api python -m scripts.seed_ml_models`"
            )
        else:
            labels = [f"{m.get('name', '?')} (id={m['id']}, {m.get('model_type', '')})" for m in models]
            model_idx = st.selectbox("Модель", range(len(models)), format_func=lambda i: labels[i])
            model_id = int(models[model_idx]["id"])
            text = st.text_area("Текст отзыва", height=160, placeholder="Введите отзыв…")
            idem = st.text_input("Idempotency-Key (необязательно)", "")
            poll_ph = st.empty()
            if st.button("Отправить", type="primary"):
                if not text or not text.strip():
                    st.error("Введите текст.")
                else:
                    try:
                        job = submit_prediction(model_id, text.strip(), idem or None)
                        st.info(f"Создано задание **#{job['id']}**, статус: `{job['status']}`")
                        final: dict[str, Any] | None
                        if job.get("status") in ("completed", "failed"):
                            final = job
                        elif job.get("status") == "queued":
                            final = poll_prediction(int(job["id"]), placeholder=poll_ph)
                        else:
                            final = job
                        if final is None:
                            st.warning("Таймаут ожидания. Проверь статус позже через API.")
                        elif final.get("status") == "completed":
                            st.session_state["_flash_prediction_ok"] = final
                            st.session_state["_pending_main_tab"] = TAB_PREDICT
                            st.rerun()
                        elif final.get("status") == "failed":
                            st.error(final.get("error_message") or "Ошибка")
                            st.json(final)
                        else:
                            st.json(final)
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 402:
                            st.error("Недостаточно кредитов — пополни кошелёк.")
                        else:
                            st.error(f"{e.response.status_code}: {e.response.text}")

    elif choice == TAB_MODELS:
        st.subheader("Доступные модели (публичный список)")
        if st.button("Обновить таблицу", key="tbl_models"):
            try:
                st.session_state["models_table"] = load_models()
                n = len(st.session_state["models_table"])
                if n == 0:
                    st.warning(
                        "В БД нет моделей. Сид: "
                        "`docker compose exec api python -m scripts.seed_ml_models`"
                    )
                else:
                    st.success(f"Строк: **{n}**")
                st.rerun()
            except httpx.HTTPStatusError as e:
                st.error(f"HTTP {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                st.error(f"Нет связи с `{API_BASE}`: {e}")
            except Exception as e:
                st.error(str(e))
        data = st.session_state.get("models_table")
        if data is None:
            if st.button("Показать модели", key="btn_models_first"):
                try:
                    st.session_state["models_table"] = load_models()
                    st.rerun()
                except httpx.HTTPStatusError as e:
                    st.error(f"HTTP {e.response.status_code}: {e.response.text}")
                except httpx.RequestError as e:
                    st.error(f"Нет связи с `{API_BASE}`: {e}")
                except Exception as e:
                    st.error(str(e))
        elif len(data) == 0:
            st.warning(
                "Таблица пуста. Запусти: "
                "`docker compose exec api python -m scripts.seed_ml_models`"
            )
        else:
            st.dataframe(
                data,
                use_container_width=True,
                hide_index=True,
            )

    elif choice == TAB_HELP:
        st.subheader("Справка: лояльность и уровни")
        st.markdown(
             """
**Как получить уровень**

- После каждого **успешного** предсказания ваш накопленный счётчик периода увеличивается,
  и **текущий уровень** сразу пересчитывается по порогам ниже.
- **Раз в месяц** (задача Celery Beat) счётчик периода **обнуляется**, а уровень выставляется
  по числу успешных предиктов за **эту** закрывающуюся отчётную серию — затем начинается новый период.

**Уровни** (скидка применяется к стоимости модели в кредитах):

| Уровень | Успешных предиктов за период (порог) | Скидка |
|---------|----------------------------------------|--------|
| **bronze** | с 0 | 0 % |
| **silver** | с 10 | 5 % |
| **gold** | с 50 | 10 % |

Скидка не опускает стоимость ниже нуля. Подробнее о сервисе — в README репозитория.
             """
        )

    elif choice == TAB_ADMIN:
        st.subheader("Администрирование")
        try:
            me = fetch_user_me()
            role = me.get("role", "user")
        except Exception as e:
            st.error(str(e))
            role = ""
        if role != "admin":
            st.warning(
                "Раздел только для роли **admin**. "
                "Добавь в `.env`: `ADMIN_BOOTSTRAP_EMAILS=твой@email` (можно несколько через запятую), "
                "перезапусти API и **войди снова** с тем же паролем — роль подтянется автоматически. "
                "Старый токен без admin не подойдёт, пока не сделаешь повторный вход."
            )
        else:
            if st.button("Обновить список пользователей", key="admin_refresh_users"):
                try:
                    st.session_state["_admin_users"] = fetch_admin_users()
                except httpx.HTTPStatusError as e:
                    st.error(f"{e.response.status_code}: {e.response.text}")
            if "_admin_users" not in st.session_state:
                if st.button("Загрузить пользователей", key="admin_load_first"):
                    try:
                        st.session_state["_admin_users"] = fetch_admin_users()
                        st.rerun()
                    except httpx.HTTPStatusError as e:
                        st.error(f"{e.response.status_code}: {e.response.text}")
            au = st.session_state.get("_admin_users")
            if isinstance(au, list):
                st.dataframe(au, use_container_width=True, hide_index=True)
                st.caption(
                    "Колонка **predictions_completed_last_30_days** — завершённые job за последние 30 дней (UTC-логика как у **`tier_name`** после обновления списка)."
                )


main()
