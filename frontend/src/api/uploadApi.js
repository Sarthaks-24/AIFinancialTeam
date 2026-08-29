import api from "./api";

export async function uploadFinancialFile(file) {

    const formData = new FormData();

    formData.append("file", file);

    const response = await api.post(
        "/upload/",
        formData,
        {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        }
    );

    return response.data;
}