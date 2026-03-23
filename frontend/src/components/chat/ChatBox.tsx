import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Image as ImageIcon, X, Smile, ChevronDown, ChevronRight } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useConversationStore } from '@/store/conversationStore'
import { useModelStore } from '@/store/modelStore'
import { useSchoolStore } from '@/store/schoolStore'
import { useTeamStore } from '@/store/teamStore'
import { useSubAgentStore } from '@/store/subAgentStore'
import { chatApi } from '@/api/chat'
import type { Message, InterruptData } from '@/types/chat'
import ConversationHistory from './ConversationHistory'
import MessageItem from './MessageItem'
import TypingIndicator from './TypingIndicator'
import InterruptDialog from './InterruptDialog'
import SubAgentModal from './SubAgentModal'
import SubAgentMinimizedBar from './SubAgentMinimizedBar'

export default function ChatBox() {
  const [input, setInput] = useState('')
  const [attachedImages, setAttachedImages] = useState<string[]>([])
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [checkpointInput, setCheckpointInput] = useState('')  // 新增：checkpoint输入
  const [outputDirInput, setOutputDirInput] = useState('')  // 新增：output目录输入
  const [currentOutputDir, setCurrentOutputDir] = useState('')  // 新增：当前output目录
  const [showOutputDirInput, setShowOutputDirInput] = useState(false)  // 新增：是否显示output目录输入框
  const [showCheckpointInput, setShowCheckpointInput] = useState(false)  // 新增：是否显示记忆添加输入框
  const [enableRAG, setEnableRAG] = useState(false)  // 新增：RAG勾选框状态
  const [currentInterrupt, setCurrentInterrupt] = useState<InterruptData | null>(null)  // 新增：当前中断状态
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const emojiPickerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)  // 新增：textarea引用

  const { selectedModelConfig } = useChatStore()
  const { selectedModel, selectedEntity } = useModelStore()
  const { getAgentSchoolInfo } = useSchoolStore()
  const { isTeamUpdating } = useTeamStore()
  const {
    currentConversationId,
    getCurrentConversation,
    selectConversation,
    createConversation,
    updateConversationMessages,
    clearCurrentConversation,
    setConversationGenerating,
    // 新增：从 conversationStore 读取消息和生成状态
    startConversationGeneration,
    stopConversationGeneration,
    updateConversationMessage,
    updateConversationMessageThinking,
    updateConversationMessageStreaming,
    updateConversationMessageIsThinking,
    setConversationTaskId,
    getConversationTaskId,
  } = useConversationStore()

  // 从 conversationStore 获取当前会话的消息和生成状态
  const currentConversation = getCurrentConversation()
  const messages = currentConversation?.messages || []
  const isGenerating = currentConversation?.isGenerating || false

  // 当选择agent或team时，自动加载该实体的对话历史
  useEffect(() => {
    if (selectedEntity) {
      // 不再停止当前正在生成的消息
      // 只清空当前对话
      clearCurrentConversation()
    }
  }, [selectedEntity?.type, selectedEntity?.entity.id])

  // 当选择对话时，加载对话内容
  useEffect(() => {
    if (currentConversationId) {
      // 不再停止当前正在生成的消息
      const conversation = getCurrentConversation()
      if (conversation) {
        // 延迟滚动到底部，确保消息已渲染
        setTimeout(() => {
          scrollToBottom()
        }, 100)
      }
    }
  }, [currentConversationId])

  // 加载当前的 output_dir
  useEffect(() => {
    const loadOutputDir = async () => {
      try {
        const result = await chatApi.getOutputDir()
        if (result.success) {
          setCurrentOutputDir(result.path)
        }
      } catch (error) {
        console.error('Failed to load output directory:', error)
      }
    }
    loadOutputDir()
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // 自动调整textarea高度
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 1000) // 最高1000px（原来的5倍）
      textarea.style.height = `${newHeight}px`
    }
  }

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    if (value.length <= 2000) {
      setInput(value)
      adjustTextareaHeight()
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 获取当前选中的实体信息（Agent 或 Team）
  const getSelectedEntityInfo = () => {
    if (!selectedEntity) return null
    
    if (selectedEntity.type === 'agent') {
      return {
        type: 'agent' as const,
        id: selectedEntity.entity.id,
        name: selectedEntity.entity.name,
        config: selectedEntity.entity
      }
    } else {
      return {
        type: 'team' as const,
        id: selectedEntity.entity.id,
        name: selectedEntity.entity.name,
        config: selectedEntity.entity
      }
    }
  }

  const handleNewConversation = () => {
    const entityInfo = getSelectedEntityInfo()
    if (!entityInfo) return
    
    // 使用实体ID创建对话（无论是Agent还是Team）
    createConversation(entityInfo.id)
  }

  const handleConversationSelect = (conversationId: string) => {
    selectConversation(conversationId)
  }

  const handleSend = async () => {
    if (!input.trim() && attachedImages.length === 0) return
    
    const entityInfo = getSelectedEntityInfo()
    if (!entityInfo) {
      alert('请先选择一个Agent或Team')
      return
    }

    // 检查当前Agent/Team是否有其他会话正在生成
    let entityId: string | null = null
    
    // 如果有当前对话，获取当前对话的agentId
    const currentConv = getCurrentConversation()
    if (currentConv) {
      entityId = currentConv.agentId
      const entityConversations = useConversationStore.getState().getConversationsByAgent(entityId)
      const generatingConv = entityConversations.find(conv => conv.isGenerating && conv.id !== currentConversationId)
      if (generatingConv) {
        alert(`当前${entityInfo.type === 'team' ? 'Team' : 'Agent'}有其他会话正在生成回答，请等待完成后再发送新消息`)
        return
      }
    } else {
      // 如果没有当前对话，使用选中的实体id
      entityId = entityInfo.id
      const entityConversations = useConversationStore.getState().getConversationsByAgent(entityId)
      const generatingConv = entityConversations.find(conv => conv.isGenerating)
      if (generatingConv) {
        alert(`当前${entityInfo.type === 'team' ? 'Team' : 'Agent'}有其他会话正在生成回答，请等待完成后再发送新消息`)
        return
      }
    }

    // 如果没有当前对话，创建新对话
    if (!currentConversationId && entityInfo) {
      createConversation(entityInfo.id)
    }

    // 重新获取当前会话ID（可能在上面创建）
    const actualConversationId = useConversationStore.getState().currentConversationId
    if (!actualConversationId) {
      alert('无法获取当前会话')
      return
    }

    // 检查agent是否在school中（仅对普通Agent）
    const schoolInfo = entityInfo.type === 'agent' && selectedModel ? getAgentSchoolInfo(selectedModel.id) : null
    const schoolId = schoolInfo?.school_id || undefined

    // 根据RAG勾选框状态，在消息前添加前缀
    const messageContent = enableRAG ? `使用知识库技能 ${input}` : input

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: messageContent,
      images: attachedImages.length > 0 ? attachedImages : undefined,
      timestamp: new Date().toISOString(),
    }

    // 获取当前会话的消息历史
    const convForMessages = getCurrentConversation()
    if (!convForMessages) {
      alert('无法获取当前会话')
      return
    }

    // 创建助手消息占位符
    const assistantMessageId = `msg_${Date.now() + 1}`
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }

    // 添加消息到会话
    const updatedMessages = [...convForMessages.messages, userMessage, assistantMessage]
    updateConversationMessages(actualConversationId, updatedMessages)

    // 清空输入
    setInput('')
    setAttachedImages([])

    // 创建AbortController以支持中断
    const abortController = new AbortController()
    
    // 更新会话的生成状态
    startConversationGeneration(actualConversationId, assistantMessageId, abortController)
    setConversationGenerating(actualConversationId, true)

    try {
      let currentContent = ''
      let currentThinking = ''

      // 根据实体类型选择不同的API调用方式
      if (entityInfo.type === 'team') {
        // Team 使用 Team 专用接口
        await chatApi.streamTeamMessage(
          {
            team_id: entityInfo.id,
            message: userMessage.content,
            images: userMessage.images,
            history: convForMessages.messages,
            conversation_id: actualConversationId,
          },
          abortController.signal,
          (chunk) => {
            // 处理流式数据块 - 所有更新都针对 actualConversationId
            console.log('[ChatBox] Received team chunk:', chunk)
            if (chunk.type === 'task_id') {
              // 保存任务ID到会话
              setConversationTaskId(actualConversationId, chunk.task_id || null)
            } else if (chunk.type === 'thinking_start') {
              // 开始思考，清空之前的thinking内容并设置思考状态
              currentThinking = ''
              updateConversationMessageThinking(actualConversationId, assistantMessageId, '')
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, true)
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
            } else if (chunk.type === 'thinking_content') {
              // 思考内容流式输出
              currentThinking += chunk.content || ''
              updateConversationMessageThinking(actualConversationId, assistantMessageId, currentThinking)
              // 保持思考状态和流式状态
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, true)
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
            } else if (chunk.type === 'thinking_end') {
              // 思考结束，标记思考完成
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
              // 保持流式状态继续输出实际内容
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
            } else if (chunk.type === 'content') {
              // 实际内容流式输出
              currentContent += chunk.content || ''
              updateConversationMessage(actualConversationId, assistantMessageId, currentContent)
              // 保持流式状态
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
            } else if (chunk.type === 'done') {
              // 完成
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
              // 清除任务ID
              setConversationTaskId(actualConversationId, null)
            } else if (chunk.type === 'cancelled') {
              // 取消
              updateConversationMessage(actualConversationId, assistantMessageId, currentContent || '任务已取消')
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
              // 清除任务ID
              setConversationTaskId(actualConversationId, null)
            } else if (chunk.type === 'error') {
              // 错误
              updateConversationMessage(actualConversationId, assistantMessageId, `生成响应时出错: ${chunk.error}`)
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
              // 清除任务ID
              setConversationTaskId(actualConversationId, null)
            } else if (chunk.type === 'checkpoint_info') {
              // checkpoint信息
              console.log('[ChatBox] Processing checkpoint_info chunk:', chunk)
              if (chunk.thread_id && chunk.checkpoint_id) {
                const checkpointInfo = {
                  thread_id: chunk.thread_id,
                  checkpoint_id: chunk.checkpoint_id,
                  parent_checkpoint_id: chunk.parent_checkpoint_id
                }
                console.log('[ChatBox] Created checkpointInfo object:', checkpointInfo)
                // 更新消息的checkpointInfo
                const conv = useConversationStore.getState().getConversationById(actualConversationId)
                if (conv) {
                  const msgIndex = conv.messages.findIndex(m => m.id === assistantMessageId)
                  if (msgIndex !== -1) {
                    const updatedMsg = {
                      ...conv.messages[msgIndex],
                      checkpointInfo
                    }
                    console.log('[ChatBox] Updated message with checkpointInfo:', updatedMsg)
                    const updatedMessages = [...conv.messages]
                    updatedMessages[msgIndex] = updatedMsg
                    updateConversationMessages(actualConversationId, updatedMessages)
                    console.log('[ChatBox] Updated conversation messages')
                  } else {
                    console.error('[ChatBox] Message not found for checkpoint_info update:', assistantMessageId)
                  }
                } else {
                  console.error('[ChatBox] Conversation not found for checkpoint_info update')
                }
              } else {
                console.error('[ChatBox] Invalid checkpoint_info chunk:', chunk)
              }
            } else if (chunk.type === 'interrupt') {
              // 中断事件
              console.log('[ChatBox] Processing interrupt chunk:', chunk)
              if (chunk.tool_name && chunk.thread_id) {
                const interruptData: InterruptData = {
                  tool_name: chunk.tool_name,
                  tool_args: chunk.tool_args || {},
                  thread_id: chunk.thread_id
                }
                console.log('[ChatBox] Created interruptData object:', interruptData)
                setCurrentInterrupt(interruptData)
              } else {
                console.error('[ChatBox] Invalid interrupt chunk:', chunk)
              }
            } else if (chunk.type === 'interrupt_rejected') {
              // 中断被拒绝（向后兼容，保留此处理）
              console.log('[ChatBox] Processing interrupt_rejected chunk:', chunk)
              setCurrentInterrupt(null)
              // 更新消息内容
              updateConversationMessage(actualConversationId, assistantMessageId, chunk.message || '工具执行被拒绝')
              updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
              updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
            }
          }
        )
      } else {
        // 普通 Agent 使用原有接口
        await chatApi.streamMessage(
          {
            model_config_id: selectedModelConfig!.id,
            message: userMessage.content,
            images: userMessage.images,
            history: convForMessages.messages,
            school_id: schoolId,
            conversation_id: actualConversationId,
          },
          abortController.signal,
          (chunk) => {
            // 处理流式数据块 - 所有更新都针对 actualConversationId
            console.log('[ChatBox] Received chunk:', chunk)
            if (chunk.type === 'task_id') {
            // 保存任务ID到会话
            setConversationTaskId(actualConversationId, chunk.task_id || null)
          } else if (chunk.type === 'thinking_start') {
            // 开始思考，清空之前的thinking内容并设置思考状态
            currentThinking = ''
            updateConversationMessageThinking(actualConversationId, assistantMessageId, '')
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, true)
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
          } else if (chunk.type === 'thinking_content') {
            // 思考内容流式输出
            currentThinking += chunk.content || ''
            updateConversationMessageThinking(actualConversationId, assistantMessageId, currentThinking)
            // 保持思考状态和流式状态
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, true)
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
          } else if (chunk.type === 'thinking_end') {
            // 思考结束，标记思考完成
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
            // 保持流式状态继续输出实际内容
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
          } else if (chunk.type === 'content') {
            // 实际内容流式输出
            currentContent += chunk.content || ''
            updateConversationMessage(actualConversationId, assistantMessageId, currentContent)
            // 保持流式状态
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, true)
          } else if (chunk.type === 'done') {
            // 完成
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
            // 清除任务ID
            setConversationTaskId(actualConversationId, null)
          } else if (chunk.type === 'cancelled') {
            // 取消
            updateConversationMessage(actualConversationId, assistantMessageId, currentContent || '任务已取消')
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
            // 清除任务ID
            setConversationTaskId(actualConversationId, null)
          } else if (chunk.type === 'error') {
            // 错误
            updateConversationMessage(actualConversationId, assistantMessageId, `生成响应时出错: ${chunk.error}`)
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
            // 清除任务ID
            setConversationTaskId(actualConversationId, null)
          } else if (chunk.type === 'checkpoint_info') {
            // checkpoint信息
            console.log('[ChatBox] Processing checkpoint_info chunk:', chunk)
            if (chunk.thread_id && chunk.checkpoint_id) {
              const checkpointInfo = {
                thread_id: chunk.thread_id,
                checkpoint_id: chunk.checkpoint_id,
                parent_checkpoint_id: chunk.parent_checkpoint_id
              }
              console.log('[ChatBox] Created checkpointInfo object:', checkpointInfo)
              // 更新消息的checkpointInfo
              const conv = useConversationStore.getState().getConversationById(actualConversationId)
              if (conv) {
                const msgIndex = conv.messages.findIndex(m => m.id === assistantMessageId)
                if (msgIndex !== -1) {
                  const updatedMsg = {
                    ...conv.messages[msgIndex],
                    checkpointInfo
                  }
                  console.log('[ChatBox] Updated message with checkpointInfo:', updatedMsg)
                  const updatedMessages = [...conv.messages]
                  updatedMessages[msgIndex] = updatedMsg
                  updateConversationMessages(actualConversationId, updatedMessages)
                  console.log('[ChatBox] Updated conversation messages')
                } else {
                  console.error('[ChatBox] Message not found for checkpoint_info update:', assistantMessageId)
                }
              } else {
                console.error('[ChatBox] Conversation not found for checkpoint_info update')
              }
            } else {
              console.error('[ChatBox] Invalid checkpoint_info chunk:', chunk)
            }
          } else if (chunk.type === 'interrupt') {
            // 中断事件
            console.log('[ChatBox] Processing interrupt chunk:', chunk)
            if (chunk.tool_name && chunk.thread_id) {
              const interruptData: InterruptData = {
                tool_name: chunk.tool_name,
                tool_args: chunk.tool_args || {},
                thread_id: chunk.thread_id
              }
              console.log('[ChatBox] Created interruptData object:', interruptData)
              setCurrentInterrupt(interruptData)
            } else {
              console.error('[ChatBox] Invalid interrupt chunk:', chunk)
            }
          } else if (chunk.type === 'interrupt_rejected') {
            // 中断被拒绝（向后兼容，保留此处理）
            console.log('[ChatBox] Processing interrupt_rejected chunk:', chunk)
            setCurrentInterrupt(null)
            // 更新消息内容
            updateConversationMessage(actualConversationId, assistantMessageId, chunk.message || '工具执行被拒绝')
            updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
            updateConversationMessageIsThinking(actualConversationId, assistantMessageId, false)
          }
        }
      )
      }  // 闭合 if (entityInfo.type === 'team') 的 else 分支

      // 更新对话历史（最终状态）
      const finalConv = useConversationStore.getState().getConversationById(actualConversationId)
      if (finalConv) {
        // 获取当前消息的checkpointInfo（如果存在）
        const currentMsg = finalConv.messages.find(m => m.id === assistantMessageId)
        const checkpointInfo = currentMsg?.checkpointInfo

        const finalAssistantMessage: Message = {
          id: assistantMessageId,
          role: 'assistant',
          content: currentContent,
          thinking: currentThinking || undefined,
          timestamp: new Date().toISOString(),
          checkpointInfo: checkpointInfo, // 保留checkpointInfo
        }
        console.log('[ChatBox] Final assistant message with checkpointInfo:', finalAssistantMessage)
        // 找到用户消息和助手消息的位置
        const userMsgIndex = finalConv.messages.findIndex(m => m.id === userMessage.id)
        const assistantMsgIndex = finalConv.messages.findIndex(m => m.id === assistantMessageId)
        
        if (userMsgIndex !== -1 && assistantMsgIndex !== -1) {
          const updatedFinalMessages = [...finalConv.messages]
          updatedFinalMessages[assistantMsgIndex] = finalAssistantMessage
          updateConversationMessages(actualConversationId, updatedFinalMessages)
          console.log('[ChatBox] Updated final conversation messages')
        }
      }
    } catch (error) {
      // 如果是用户主动中断，不显示错误消息
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Message generation was interrupted')
        updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
        return
      }

      console.error('Failed to send message:', error)
      updateConversationMessage(actualConversationId, assistantMessageId, `发送消息失败: ${error instanceof Error ? error.message : '未知错误'}`)
      updateConversationMessageStreaming(actualConversationId, assistantMessageId, false)
    } finally {
      // 确保生成状态被重置
      stopConversationGeneration(actualConversationId)
      setConversationGenerating(actualConversationId, false)
      // 清除任务ID
      setConversationTaskId(actualConversationId, null)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCheckpointReload = async () => {
    if (!checkpointInput.trim()) {
      alert('请输入Checkpoint ID')
      return
    }

    const entityInfo = getSelectedEntityInfo()
    if (!entityInfo) {
      alert('请先选择一个Agent或Team配置')
      return
    }

    if (!currentConversationId) {
      alert('请先选择或创建一个对话')
      return
    }

    try {
      const result = await chatApi.addCheckpoint(
        entityInfo.id,
        checkpointInput.trim(),
        currentConversationId
      )

      if (result.success) {
        // 创建系统提示消息
        const systemMessage: Message = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: '记忆添加成功！',
          timestamp: new Date().toISOString(),
        }
        // 添加系统消息到会话
        const conv = getCurrentConversation()
        if (conv) {
          const updatedMessages = [...conv.messages, systemMessage]
          if (currentConversationId) {
            updateConversationMessages(currentConversationId, updatedMessages)
          }
        }

        setCheckpointInput('')
      } else {
        // 创建系统错误消息
        const systemMessage: Message = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: `记忆添加失败：${result.message}`,
          timestamp: new Date().toISOString(),
        }
        // 添加系统消息到会话
        const conv = getCurrentConversation()
        if (conv) {
          const updatedMessages = [...conv.messages, systemMessage]
          if (currentConversationId) {
            updateConversationMessages(currentConversationId, updatedMessages)
          }
        }
      }
    } catch (error) {
      console.error('Failed to copy checkpoint:', error)
      // 创建系统错误消息
      const systemMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `记忆添加失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toISOString(),
      }
      // 添加系统消息到会话
      const conv = getCurrentConversation()
      if (conv) {
        const updatedMessages = [...conv.messages, systemMessage]
        if (currentConversationId) {
          updateConversationMessages(currentConversationId, updatedMessages)
        }
      }
    }
  }

  const handleSetOutputDir = async () => {
    if (!outputDirInput.trim()) {
      alert('请输入Output目录路径')
      return
    }

    // 验证路径是否为绝对路径
    const path = outputDirInput.trim()
    if (!path.match(/^[A-Za-z]:\\/)) {  // Windows 绝对路径检查
      alert('请输入有效的绝对路径（例如：C:\\Users\\YourName\\output）')
      return
    }

    try {
      const result = await chatApi.setOutputDir(path)
      if (result.success) {
        setCurrentOutputDir(result.path)
        setOutputDirInput('')
        setShowOutputDirInput(false)
        // 创建系统提示消息
        const systemMessage: Message = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: `Output目录已更新为：${result.path}`,
          timestamp: new Date().toISOString(),
        }
        // 添加系统消息到会话
        const conv = getCurrentConversation()
        if (conv) {
          const updatedMessages = [...conv.messages, systemMessage]
          if (currentConversationId) {
            updateConversationMessages(currentConversationId, updatedMessages)
          }
        }
      } else {
        // 创建系统错误消息
        const systemMessage: Message = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: `设置失败：${result.message}`,
          timestamp: new Date().toISOString(),
        }
        // 添加系统消息到会话
        const conv = getCurrentConversation()
        if (conv) {
          const updatedMessages = [...conv.messages, systemMessage]
          if (currentConversationId) {
            updateConversationMessages(currentConversationId, updatedMessages)
          }
        }
      }
    } catch (error) {
      console.error('Failed to set output directory:', error)
      // 创建系统错误消息
      const systemMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `设置失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toISOString(),
      }
      // 添加系统消息到会话
      const conv = getCurrentConversation()
      if (conv) {
        const updatedMessages = [...conv.messages, systemMessage]
        if (currentConversationId) {
          updateConversationMessages(currentConversationId, updatedMessages)
        }
      }
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'))
      
      // 检查是否超过5张图片限制
      if (attachedImages.length + imageFiles.length > 5) {
        alert(`一次最多可以发送5张图片，当前已选择${attachedImages.length}张，还可以选择${5 - attachedImages.length}张`)
        return
      }
      
      // 读取所有图片
      imageFiles.forEach(file => {
        const reader = new FileReader()
        reader.onloadend = () => {
          setAttachedImages(prev => [...prev, reader.result as string])
        }
        reader.readAsDataURL(file)
      })
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (items) {
      const imageFiles: File[] = []
      
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile()
          if (file) {
            imageFiles.push(file)
          }
        }
      }
      
      // 检查是否超过5张图片限制
      if (attachedImages.length + imageFiles.length > 5) {
        alert(`一次最多可以发送5张图片，当前已选择${attachedImages.length}张，还可以粘贴${5 - attachedImages.length}张`)
        return
      }
      
      // 读取所有粘贴的图片
      imageFiles.forEach(file => {
        const reader = new FileReader()
        reader.onloadend = () => {
          setAttachedImages(prev => [...prev, reader.result as string])
        }
        reader.readAsDataURL(file)
      })
    }
  }

  // 表情列表
  const emojis = [
    '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
    '🙂', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗',
    '😚', '😙', '😋', '😛', '😜', '🤪', '😝', '🤑',
    '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑',
    '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔',
    '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮',
    '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳',
    '😎', '🤓', '🧐', '😕', '😟', '🙁', '☹️', '😮',
    '😯', '😲', '😳', '🥺', '😦', '😧', '😨', '😰',
    '😥', '😢', '😭', '😱', '😖', '😣', '😞', '😓',
    '😩', '😫', '🥱', '😤', '😡', '😠', '🤬', '👍',
    '👎', '👏', '🙌', '🤝', '❤️', '🧡', '💛', '💚',
    '💙', '💜', '🖤', '🤍', '🤎', '💔', '💕', '💖',
    '💗', '💘', '💝', '💞', '🌟', '⭐', '✨', '💫',
    '🎉', '🎊', '🎈', '🎁', '🎀', '🏆', '🥇', '🥈',
    '🥉', '🔥', '💪', '👏', '🙌', '👋', '🤝', '✌️'
  ]

  const handleEmojiClick = (emoji: string) => {
    setInput(prev => prev + emoji)
    setShowEmojiPicker(false)
  }

  // 点击外部关闭表情选择器
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target as Node)) {
        setShowEmojiPicker(false)
      }
    }

    if (showEmojiPicker) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showEmojiPicker])

  // 获取当前选中的实体信息，用于渲染
  const entityInfo = getSelectedEntityInfo()

  // 检查当前选中的 Team 是否正在更新
  const isCurrentTeamUpdating = entityInfo?.type === 'team' && isTeamUpdating(entityInfo.id)

  // SubAgent Store
  const visibleModalIds = useSubAgentStore((state) => state.visibleModalIds)
  const closeModal = useSubAgentStore((state) => state.closeModal)
  const minimizeModal = useSubAgentStore((state) => state.minimizeModal)
  const restoreModal = useSubAgentStore((state) => state.restoreModal)
  const removeExecution = useSubAgentStore((state) => state.removeExecution)

  // 监听 visibleModalIds 变化
  useEffect(() => {
    console.log('[ChatBox] visibleModalIds 变化:', visibleModalIds)
  }, [visibleModalIds])

  // 计算每个弹窗的位置（错开显示）
  const getModalPosition = (index: number) => {
    const baseX = 100
    const baseY = 100
    const offset = 30
    return {
      x: baseX + index * offset,
      y: baseY + index * offset,
    }
  }

  return (
    <div className="h-full flex">
      <div className="flex-1 flex flex-col bg-white">
        <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
          {!entityInfo ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-16 h-16 mb-4 bg-gray-100 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-lg font-medium">开始对话</p>
              <p className="text-sm">请先选择一个Agent或Team配置</p>
            </div>
          ) : !currentConversationId ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-16 h-16 mb-4 bg-gray-100 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-lg font-medium">请选择一个对话</p>
              <p className="text-sm">从右侧对话历史中选择，或创建新对话</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-16 h-16 mb-4 bg-gray-100 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-lg font-medium">开始对话</p>
              <p className="text-sm">输入您的消息开始聊天</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 relative">
              {/* Team 更新遮罩 */}
              {isCurrentTeamUpdating && (
                <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center rounded-lg">
                  <div className="flex items-center space-x-3 bg-amber-50 border border-amber-200 rounded-lg px-6 py-4 shadow-lg">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-600"></div>
                    <span className="text-amber-800 font-medium">Team 正在更新中，请稍候...</span>
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <MessageItem
                  key={message.id}
                  message={message}
                  agentName={entityInfo?.name}
                />
              ))}
              {isGenerating && (
                <TypingIndicator agentName={entityInfo?.name} />
              )}

              {/* 显示中断对话框 - 移到消息列表底部 */}
              {currentInterrupt && (
                <InterruptDialog
                  interrupt={currentInterrupt}
                  onDecision={(decision) => {
                    console.log('[ChatBox] Interrupt decision:', decision)
                    // 无论同意还是拒绝，后端都会继续执行（使用 Command 恢复）
                    // 所以前端在用户做出决策后立即关闭对话框
                    setCurrentInterrupt(null)
                  }}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {currentConversationId && (
          <div className={`p-4 ${isCurrentTeamUpdating ? 'pointer-events-none opacity-50' : ''}`}>
            {/* Output 目录配置 UI */}
            <div className="max-w-3xl mx-auto mb-4">
              <div className="bg-gray-50 rounded-lg">
                <button
                  onClick={() => setShowOutputDirInput(!showOutputDirInput)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    {showOutputDirInput ? (
                      <ChevronDown className="w-4 h-4 text-gray-600" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-600" />
                    )}
                    <span className="text-sm font-medium text-gray-700">Output 目录配置</span>
                  </div>
                  <div className="text-xs text-gray-500 truncate max-w-[200px]">{currentOutputDir || '加载中...'}</div>
                </button>
                {showOutputDirInput && (
                  <div className="px-4 pb-3">
                    <div className="mb-2">
                      <div className="text-sm text-gray-600 mb-1">当前 Output 目录：</div>
                      <div className="text-sm font-mono text-gray-800 truncate">{currentOutputDir || '加载中...'}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={outputDirInput}
                        onChange={(e) => setOutputDirInput(e.target.value)}
                        placeholder="输入绝对路径（例如：C:\\Users\\YourName\\output）"
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                      />
                      <button
                        onClick={handleSetOutputDir}
                        disabled={!outputDirInput.trim()}
                        className="px-4 py-2 text-sm text-white bg-gradient-primary rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                      >
                        确认
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 记忆添加UI */}
            <div className="max-w-3xl mx-auto mb-4">
              <div className="bg-gray-50 rounded-lg">
                <button
                  onClick={() => setShowCheckpointInput(!showCheckpointInput)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    {showCheckpointInput ? (
                      <ChevronDown className="w-4 h-4 text-gray-600" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-600" />
                    )}
                    <span className="text-sm font-medium text-gray-700">添加记忆</span>
                  </div>
                </button>
                {showCheckpointInput && (
                  <div className="px-4 pb-3">
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={checkpointInput}
                        onChange={(e) => setCheckpointInput(e.target.value)}
                        placeholder="输入Checkpoint ID以添加记忆..."
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      <button
                        onClick={handleCheckpointReload}
                        disabled={!checkpointInput.trim()}
                        className="px-4 py-2 text-sm text-white bg-gradient-primary rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                      >
                        添加
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* RAG勾选框UI */}
            <div className="max-w-3xl mx-auto mb-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="rag-checkbox"
                  checked={enableRAG}
                  onChange={(e) => setEnableRAG(e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
                />
                <label
                  htmlFor="rag-checkbox"
                  className="text-sm text-gray-700 cursor-pointer select-none"
                >
                  启用RAG（知识库检索增强生成）
                </label>
              </div>
            </div>

            {attachedImages.length > 0 && (
              <div className="mb-3">
                <div className="flex flex-wrap gap-2">
                  {attachedImages.map((image, index) => (
                    <div key={index} className="relative inline-block">
                      <img
                        src={image}
                        alt={`Attached ${index + 1}`}
                        className="max-h-32"
                      />
                      <button
                        onClick={() => setAttachedImages(prev => prev.filter((_, i) => i !== index))}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white text-sm hover:bg-red-600 flex items-center justify-center rounded-full"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">已选择 {attachedImages.length}/5 张图片</p>
              </div>
            )}

            <div className="max-w-3xl mx-auto flex items-end space-x-2 relative">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/*"
                multiple
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="h-12 w-12 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <div className="relative" ref={emojiPickerRef}>
                <button
                  onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                  className="h-12 w-12 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
                >
                  <Smile className="w-5 h-5" />
                </button>
                {showEmojiPicker && (
                  <div className="absolute bottom-14 left-0 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 max-h-64 overflow-y-auto w-96">
                    <div className="grid grid-cols-10 gap-1">
                      {emojis.map((emoji, index) => (
                        <button
                          key={index}
                          onClick={() => handleEmojiClick(emoji)}
                          className="w-8 h-8 flex items-center justify-center text-xl hover:bg-gray-100 rounded transition-colors"
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyPress={handleKeyPress}
                  onPaste={handlePaste}
                  placeholder="输入您的消息...（按 Enter 发送，Shift+Enter 换行，最多5张图片）"
                  className="w-full resize-none px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500 shadow-elegant"
                  rows={1}
                  maxLength={2000}
                  style={{ minHeight: '48px', maxHeight: '1000px' }}
                />
                <div className="absolute bottom-1 right-2 text-xs text-gray-400">
                  {input.length}/2000
                </div>
              </div>
              <button
                onClick={async () => {
                  if (isGenerating && currentConversationId) {
                    // 只有当前会话正在生成时才允许取消
                    const currentConv = getCurrentConversation()
                    if (currentConv && currentConv.isGenerating) {
                      // 如果有任务ID，使用任务ID取消
                      const convTaskId = getConversationTaskId(currentConversationId)
                      if (convTaskId) {
                        await chatApi.cancelTask(convTaskId)
                      }
                      // 停止会话生成
                      stopConversationGeneration(currentConversationId)
                      setConversationGenerating(currentConversationId, false)
                    }
                  } else {
                    handleSend()
                  }
                }}
                disabled={!input.trim() && attachedImages.length === 0 && !isGenerating}
                className={`h-12 w-12 flex items-center justify-center text-white shadow-elegant hover:shadow-elegant-hover disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors ${
                  isGenerating ? 'bg-danger-500 hover:bg-danger-600' : 'bg-gradient-primary'
                }`}
              >
                {isGenerating ? <X className="w-5 h-5" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </div>
        )}
      </div>

      <ConversationHistory
        agentId={entityInfo?.id || null}
        onNewConversation={handleNewConversation}
        onConversationSelect={handleConversationSelect}
      />

      {/* SUB Agent 弹窗 */}
      {visibleModalIds.map((executionId, index) => {
        console.log('[ChatBox] 渲染 SubAgentModal:', executionId)
        return (
          <SubAgentModal
            key={executionId}
            executionId={executionId}
            onClose={() => closeModal(executionId)}
            onMinimize={() => minimizeModal(executionId)}
            initialPosition={getModalPosition(index)}
          />
        )
      })}

      {/* SUB Agent 最小化悬浮栏 */}
      <SubAgentMinimizedBar
        onRestore={(executionId) => restoreModal(executionId)}
        onClose={(executionId) => {
          closeModal(executionId)
          removeExecution(executionId)
        }}
      />
    </div>
  )
}
