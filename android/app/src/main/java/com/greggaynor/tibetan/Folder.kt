package com.greggaynor.tibetan

import android.content.Context
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.DocumentsContract.Document

/**
 * The data folder on the phone (usually a synced "tibetan" folder), reached through the Storage
 * Access Framework (picked once; the permission persists). Paths are relative to that folder,
 * e.g. "app/content.json" or "progress/<device>.jsonl".
 */
class Folder(ctx: Context, private val tree: Uri) {
    private val cr = ctx.contentResolver
    private val root = DocumentsContract.getTreeDocumentId(tree)

    private data class Entry(val id: String, val name: String, val mime: String)

    private fun docUri(id: String): Uri = DocumentsContract.buildDocumentUriUsingTree(tree, id)

    private fun children(parent: String): List<Entry> {
        val uri = DocumentsContract.buildChildDocumentsUriUsingTree(tree, parent)
        val out = ArrayList<Entry>()
        cr.query(uri, arrayOf(Document.COLUMN_DOCUMENT_ID, Document.COLUMN_DISPLAY_NAME, Document.COLUMN_MIME_TYPE), null, null, null)?.use { c ->
            while (c.moveToNext()) out.add(Entry(c.getString(0), c.getString(1), c.getString(2) ?: ""))
        }
        return out
    }

    private fun find(path: String): String? {
        var id = root
        for (seg in path.split('/').filter { it.isNotEmpty() }) {
            id = children(id).firstOrNull { it.name == seg }?.id ?: return null
        }
        return id
    }

    /** Find a sub-folder, creating it if needed. */
    private fun dir(path: String): String? {
        var id = root
        for (seg in path.split('/').filter { it.isNotEmpty() }) {
            val existing = children(id).firstOrNull { it.name == seg && it.mime == Document.MIME_TYPE_DIR }
            id = existing?.id
                ?: DocumentsContract.createDocument(cr, docUri(id), Document.MIME_TYPE_DIR, seg)?.let { DocumentsContract.getDocumentId(it) }
                ?: return null
        }
        return id
    }

    fun read(path: String): String? {
        val id = find(path) ?: return null
        return cr.openInputStream(docUri(id))?.use { it.readBytes().toString(Charsets.UTF_8) }
    }

    fun list(dir: String): List<String> {
        val id = find(dir) ?: return emptyList()
        return children(id).filter { it.mime != Document.MIME_TYPE_DIR }.map { it.name }.sorted()
    }

    /** Append to this device's progress log (created on first use). One writer per file, so a sync tool never sees a conflict. */
    fun append(path: String, text: String): Boolean {
        val dirId = dir(path.substringBeforeLast('/', "")) ?: return false
        val name = path.substringAfterLast('/')
        val existing = children(dirId).firstOrNull { it.name == name }
        // octet-stream so the provider keeps the .jsonl name instead of adding ".txt"
        val uri = existing?.let { docUri(it.id) }
            ?: DocumentsContract.createDocument(cr, docUri(dirId), "application/octet-stream", name)
            ?: return false
        cr.openOutputStream(uri, "wa")?.use { it.write(text.toByteArray(Charsets.UTF_8)) } ?: return false
        return true
    }

    /** Write a new file (a pasted class note); never overwrites. */
    fun create(path: String, text: String): Boolean {
        val dirId = dir(path.substringBeforeLast('/', "")) ?: return false
        val name = path.substringAfterLast('/')
        if (children(dirId).any { it.name == name }) return false
        val uri = DocumentsContract.createDocument(cr, docUri(dirId), "text/plain", name) ?: return false
        cr.openOutputStream(uri, "w")?.use { it.write(text.toByteArray(Charsets.UTF_8)) } ?: return false
        return true
    }
}
